"""Database session management with MySQL auto-creation and resilient reconnects."""

import re
import ssl
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import unquote, urlparse

import pymysql
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.logging import logger
from app.models.database import Base

_engine = None
_session_factory = None
_memory_records: list[dict[str, Any]] = []
_db_available = False


def _parse_mysql_url(url: str) -> dict[str, Any]:
    """Parse mysql+aiomysql://user:pass@host:port/dbname into connection parts."""
    normalized = url.replace("mysql+aiomysql://", "mysql://").replace("mysql+pymysql://", "mysql://")
    parsed = urlparse(normalized)
    db_name = parsed.path.lstrip("/") or "truthtrace"
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or "root"),
        "password": unquote(parsed.password or ""),
        "database": db_name,
    }


def _is_hosted_mysql(url: str) -> bool:
    """Return True for cloud-hosted MySQL providers that manage the DB themselves."""
    hosted_patterns = ["aivencloud.com", "planetscale", "railway.app", "supabase", "render.com"]
    return any(p in url for p in hosted_patterns)


def _needs_ssl(url: str) -> bool:
    """Return True when the connection requires SSL (Aiven enforces it)."""
    settings = get_settings()
    if settings.database_ssl_required:
        return True
    ssl_providers = ["aivencloud.com", "planetscale", "supabase"]
    return any(p in url for p in ssl_providers)


def _is_production_db() -> bool:
    """True when using an external hosted database (data must survive restarts)."""
    settings = get_settings()
    url = settings.database_url
    if _is_hosted_mysql(url):
        return True
    # Any non-localhost URL is treated as production
    return "localhost" not in url and "127.0.0.1" not in url


def ensure_mysql_database() -> None:
    """Create the MySQL database if it does not exist (local dev only)."""
    settings = get_settings()
    if not settings.database_url.startswith("mysql"):
        return

    if _is_hosted_mysql(settings.database_url):
        logger.info("mysql_database_skipped", reason="hosted_provider")
        return

    parts = _parse_mysql_url(settings.database_url)
    db_name = parts.pop("database")

    if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
        raise ValueError(f"Invalid database name: {db_name}")

    try:
        conn = pymysql.connect(**parts, charset="utf8mb4")
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        conn.close()
        logger.info("mysql_database_ready", database=db_name)
    except Exception as e:
        logger.warning("mysql_database_create_failed", error=str(e))


def _build_connect_args(url: str) -> dict[str, Any]:
    """Build aiomysql connect_args including SSL for Aiven."""
    connect_args: dict[str, Any] = {"connect_timeout": 30}
    if _needs_ssl(url):
        # Aiven requires TLS; use default verified context
        connect_args["ssl"] = ssl.create_default_context()
        logger.info("database_ssl_enabled")
    return connect_args


async def init_db() -> None:
    global _engine, _session_factory, _db_available
    settings = get_settings()

    db_url = settings.database_url
    # Render/Aiven often provide mysql:// — SQLAlchemy async needs mysql+aiomysql://
    if db_url.startswith("mysql://"):
        db_url = db_url.replace("mysql://", "mysql+aiomysql://", 1)

    if not db_url.startswith("mysql"):
        logger.warning("unsupported_database_url", url=db_url[:30])
        _db_available = False
        return

    try:
        ensure_mysql_database()
        connect_args = _build_connect_args(db_url)

        _engine = create_async_engine(
            db_url,
            echo=settings.debug,
            pool_pre_ping=False,  # aiomysql ping() is unreliable; we reconnect explicitly
            pool_recycle=240,     # Recycle before Aiven idle timeout (~300s)
            pool_size=3,
            max_overflow=5,
            connect_args=connect_args,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("SELECT 1"))

        _db_available = True
        count = await get_record_count()
        logger.info(
            "database_initialized",
            driver="mysql",
            ssl=bool(connect_args.get("ssl")),
            records=count,
        )
    except Exception as e:
        logger.warning("database_unavailable", error=str(e))
        _engine = None
        _session_factory = None
        _db_available = False


async def _dispose_engine() -> None:
    """Tear down the connection pool (used after stale connections on Render wake-up)."""
    global _engine, _session_factory, _db_available
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception as e:
            logger.warning("engine_dispose_failed", error=str(e))
    _engine = None
    _session_factory = None
    _db_available = False


async def _force_reconnect() -> bool:
    """Dispose stale pool and re-initialise. Returns True if DB is reachable."""
    logger.info("database_force_reconnect")
    await _dispose_engine()
    await init_db()
    return _db_available


def is_db_available() -> bool:
    return _db_available


async def get_session() -> AsyncSession | None:
    if _session_factory is None:
        return None
    return _session_factory()


async def get_record_count() -> int:
    """Return total verification records in MySQL (0 if unavailable)."""
    session = await get_session()
    if session is None:
        return 0

    from app.models.database import VerificationRecord

    try:
        async with session:
            result = await session.execute(select(func.count()).select_from(VerificationRecord))
            return int(result.scalar() or 0)
    except Exception as e:
        logger.error("record_count_failed", error=str(e))
        return 0


async def save_verification(result: dict, session_id: str | None = None) -> None:
    """Persist verification result to MySQL (required in production)."""
    memory_record = {
        **result,
        "session_id": session_id,
        "sources_count": len(result.get("sources", [])),
        "contradictions_count": len(result.get("contradictions", [])),
        "created_at": result.get("created_at") or datetime.now(timezone.utc).isoformat(),
    }
    _memory_records.append(memory_record)
    if len(_memory_records) > 1000:
        del _memory_records[:-1000]

    from app.models.database import VerificationRecord

    for attempt in range(3):
        session = await get_session()
        if session is None:
            if await _force_reconnect():
                continue
            break

        try:
            async with session:
                record = VerificationRecord(
                    session_id=session_id,
                    question=result["question"],
                    answer=result["answer"],
                    confidence_score=float(result["confidence_score"]),
                    verification_status=result["verification_status"],
                    sources_count=len(result.get("sources", [])),
                    contradictions_count=len(result.get("contradictions", [])),
                    sources=result.get("sources", []),
                    contradictions=result.get("contradictions", []),
                    trust_report=result.get("trust_report", {}),
                    claims=result.get("claims", []),
                )
                session.add(record)
                await session.commit()
                logger.info(
                    "verification_saved_to_mysql",
                    question=result["question"][:50],
                    attempt=attempt + 1,
                )
                return
        except Exception as e:
            logger.error("save_verification_failed", error=str(e), attempt=attempt + 1)
            await _force_reconnect()

    if _is_production_db():
        logger.error(
            "verification_not_persisted",
            question=result["question"][:50],
            reason="all_mysql_save_attempts_failed",
        )


async def get_verification_history(limit: int = 20) -> dict:
    records = await _load_records()
    records = sorted(records, key=lambda r: _coerce_datetime(r.get("created_at")), reverse=True)
    return {"records": records[:limit], "total": len(records)}


async def get_dashboard_stats() -> dict:
    records = await _load_records()
    return _build_dashboard_stats(records)


async def _load_records() -> list[dict[str, Any]]:
    """Load verification records from MySQL with reconnect retries."""
    from app.models.database import VerificationRecord

    for attempt in range(3):
        session = await get_session()
        if session is None:
            if await _force_reconnect():
                continue
            break

        try:
            async with session:
                result = await session.execute(
                    select(VerificationRecord)
                    .order_by(VerificationRecord.created_at.desc())
                    .limit(1000)
                )
                rows = result.scalars().all()
                db_records = [_record_to_dict(row) for row in rows]
                logger.debug("records_loaded_from_mysql", count=len(db_records), attempt=attempt + 1)
                return db_records
        except Exception as e:
            logger.error("load_verifications_failed", error=str(e), attempt=attempt + 1)
            await _force_reconnect()

    # Production: never mask a DB outage with empty in-memory data after Render restarts
    if _is_production_db():
        logger.error("load_verifications_exhausted_retries", fallback="empty")
        return []

    return list(_memory_records)


def _record_to_dict(record: Any) -> dict[str, Any]:
    created = record.created_at
    if isinstance(created, datetime):
        created_str = created.isoformat()
    else:
        created_str = str(created)
    return {
        "id": str(record.id),
        "session_id": record.session_id,
        "question": record.question,
        "answer": record.answer,
        "confidence_score": record.confidence_score,
        "verification_status": record.verification_status,
        "sources_count": record.sources_count,
        "contradictions_count": record.contradictions_count,
        "sources": record.sources or [],
        "contradictions": record.contradictions or [],
        "trust_report": record.trust_report or {},
        "claims": record.claims or [],
        "created_at": created_str,
    }


def _build_dashboard_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    if total == 0:
        return {
            "total_queries": 0,
            "verification_rate": 0.0,
            "average_confidence": 0.0,
            "sources_used": 0,
            "confidence_trend": [],
            "verification_history": [],
            "source_reliability": [],
        }

    verified_count = sum(1 for r in records if r.get("verification_status") == "verified")
    average_confidence = round(
        sum(float(r.get("confidence_score") or 0) for r in records) / total,
        1,
    )
    sources_used = sum(int(r.get("sources_count") or len(r.get("sources", []))) for r in records)

    today = datetime.now(timezone.utc).date()
    daily: dict[str, dict[str, Any]] = {}
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        label = day.strftime("%b %d")
        daily[label] = {
            "date": label,
            "scores": [],
            "verified": 0,
            "partial": 0,
            "unverified": 0,
        }

    domain_scores: defaultdict[str, list[float]] = defaultdict(list)
    domain_counts: Counter[str] = Counter()

    for record in records:
        created = _coerce_datetime(record.get("created_at")).date()
        label = created.strftime("%b %d")
        if label in daily:
            daily[label]["scores"].append(float(record.get("confidence_score") or 0))
            status = record.get("verification_status") or "unverified"
            if status not in {"verified", "partial", "unverified"}:
                status = "unverified"
            daily[label][status] += 1

        for source in record.get("sources", []) or []:
            domain = source.get("domain") if isinstance(source, dict) else None
            score = source.get("reliability_score") if isinstance(source, dict) else None
            if domain and score is not None:
                domain_counts[domain] += 1
                domain_scores[domain].append(float(score))

    confidence_trend = [
        {
            "date": item["date"],
            "score": round(sum(item["scores"]) / len(item["scores"]), 1) if item["scores"] else 0,
        }
        for item in daily.values()
    ]
    verification_history = [
        {
            "date": item["date"],
            "verified": item["verified"],
            "partial": item["partial"],
            "unverified": item["unverified"],
        }
        for item in daily.values()
    ]
    source_reliability = [
        {
            "domain": domain,
            "score": round(sum(domain_scores[domain]) / len(domain_scores[domain]), 1),
            "count": count,
        }
        for domain, count in domain_counts.most_common(8)
    ]

    return {
        "total_queries": total,
        "verification_rate": round((verified_count / total) * 100, 1),
        "average_confidence": average_confidence,
        "sources_used": sources_used,
        "confidence_trend": confidence_trend,
        "verification_history": verification_history,
        "source_reliability": source_reliability,
    }


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)
