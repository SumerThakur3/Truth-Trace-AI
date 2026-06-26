"""Database session management with MySQL auto-creation and resilient reconnects."""

import re
import ssl
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import pymysql
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db_url import (
    database_host_hint,
    get_resolved_db_url,
    is_hosted_mysql_url,
    is_render,
)
from app.core.logging import logger
from app.models.database import Base

_engine = None
_session_factory = None
_memory_records: list[dict[str, Any]] = []
_db_available = False
_last_db_error: str | None = None
_active_db_url: str | None = None


def _parse_mysql_url(url: str) -> dict[str, Any]:
    """Parse mysql URL into pymysql connection parts."""
    from urllib.parse import unquote, urlparse

    normalized = url.replace("mysql+aiomysql://", "mysql://").replace("mysql+pymysql://", "mysql://")
    parsed = urlparse(normalized)
    db_name = parsed.path.lstrip("/") or "defaultdb"
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or "root"),
        "password": unquote(parsed.password or ""),
        "database": db_name,
    }


def _needs_ssl(url: str) -> bool:
    settings = get_settings()
    if settings.database_ssl_required:
        return True
    if is_hosted_mysql_url(url):
        return True
    if is_render() and not ("localhost" in url or "127.0.0.1" in url):
        return True
    return False


def _is_production_db() -> bool:
    url = _active_db_url or get_resolved_db_url()
    if is_hosted_mysql_url(url):
        return True
    return "localhost" not in url and "127.0.0.1" not in url


def _ssl_strategies() -> list[dict[str, Any]]:
    """Ordered SSL strategies for Aiven / Render (try strict first, then fallbacks)."""
    settings = get_settings()
    strategies: list[dict[str, Any]] = []

    if settings.database_ssl_ca:
        ctx = ssl.create_default_context(cafile=settings.database_ssl_ca)
        strategies.append({"ssl": ctx, "label": "ca_file"})

    ctx_verified = ssl.create_default_context()
    strategies.append({"ssl": ctx_verified, "label": "verified"})

    # aiomysql accepts plain True for encrypted connection
    strategies.append({"ssl": True, "label": "ssl_true"})

    # Render containers sometimes lack CA bundle — required fallback for Aiven
    ctx_relaxed = ssl.create_default_context()
    ctx_relaxed.check_hostname = False
    ctx_relaxed.verify_mode = ssl.CERT_NONE
    strategies.append({"ssl": ctx_relaxed, "label": "relaxed"})

    return strategies


def _connect_arg_variants(url: str) -> list[tuple[str, dict[str, Any]]]:
    """Build connect_args variants to try at startup."""
    base: dict[str, Any] = {"connect_timeout": 30}
    variants: list[tuple[str, dict[str, Any]]] = []

    if _needs_ssl(url):
        for strat in _ssl_strategies():
            args = {**base, "ssl": strat["ssl"]}
            variants.append((strat["label"], args))
    else:
        variants.append(("no_ssl", base))

    return variants


def _sync_ping(url: str, connect_args: dict[str, Any]) -> None:
    """Validate credentials with pymysql before creating async pool."""
    parts = _parse_mysql_url(url)
    ssl_arg = connect_args.get("ssl")
    kwargs: dict[str, Any] = {
        **parts,
        "charset": "utf8mb4",
        "connect_timeout": connect_args.get("connect_timeout", 30),
    }
    if ssl_arg is not None:
        kwargs["ssl"] = ssl_arg

    conn = pymysql.connect(**kwargs)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        conn.close()


def ensure_mysql_database(url: str) -> None:
    """Create database locally only (never on Aiven/Render)."""
    if is_hosted_mysql_url(url) or is_render():
        logger.info("mysql_database_skipped", reason="hosted_provider")
        return

    parts = _parse_mysql_url(url)
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


async def init_db() -> None:
    global _engine, _session_factory, _db_available, _last_db_error, _active_db_url

    settings = get_settings()

    try:
        db_url = get_resolved_db_url()
    except ValueError as e:
        _last_db_error = str(e)
        _db_available = False
        logger.error("database_url_invalid", error=str(e))
        return

    _active_db_url = db_url
    host = database_host_hint(db_url)

    if _is_localhost_url(db_url) and is_render():
        _last_db_error = (
            "DATABASE_URL points to localhost on Render. "
            "Set DATABASE_URL to your Aiven mysql+aiomysql:// connection string, "
            "or set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE on Render."
        )
        logger.error("database_misconfigured", host=host, render=True)
        _db_available = False
        return

    ensure_mysql_database(db_url)
    last_error: Exception | None = None

    for label, connect_args in _connect_arg_variants(db_url):
        try:
            _sync_ping(db_url, connect_args)
            logger.info("database_sync_ping_ok", host=host, ssl_mode=label)

            _engine = create_async_engine(
                db_url,
                echo=settings.debug,
                pool_pre_ping=False,
                pool_recycle=240,
                pool_size=3,
                max_overflow=5,
                connect_args=connect_args,
            )
            _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(text("SELECT 1"))

            _db_available = True
            _last_db_error = None
            count = await get_record_count()
            logger.info(
                "database_initialized",
                host=host,
                ssl_mode=label,
                records=count,
            )
            return
        except Exception as e:
            last_error = e
            logger.warning(
                "database_connect_attempt_failed",
                host=host,
                ssl_mode=label,
                error=str(e)[:300],
            )
            if _engine is not None:
                try:
                    await _engine.dispose()
                except Exception:
                    pass
            _engine = None
            _session_factory = None

    _db_available = False
    _last_db_error = str(last_error)[:500] if last_error else "Unknown connection error"
    logger.error("database_unavailable", host=host, error=_last_db_error)


def _is_localhost_url(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


async def _dispose_engine() -> None:
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
    logger.info("database_force_reconnect")
    await _dispose_engine()
    await init_db()
    return _db_available


def is_db_available() -> bool:
    return _db_available


def get_last_db_error() -> str | None:
    return _last_db_error


def get_db_status() -> dict[str, Any]:
    url = _active_db_url or get_resolved_db_url()
    return {
        "available": _db_available,
        "host": database_host_hint(url),
        "error": _last_db_error,
        "render": is_render(),
    }


async def get_session() -> AsyncSession | None:
    if _session_factory is None:
        return None
    return _session_factory()


async def get_record_count() -> int:
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
                return [_record_to_dict(row) for row in rows]
        except Exception as e:
            logger.error("load_verifications_failed", error=str(e), attempt=attempt + 1)
            await _force_reconnect()

    if _is_production_db():
        return []

    return list(_memory_records)


def _record_to_dict(record: Any) -> dict[str, Any]:
    created = record.created_at
    created_str = created.isoformat() if isinstance(created, datetime) else str(created)
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
