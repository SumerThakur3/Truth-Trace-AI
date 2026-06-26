"""API route handlers."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import VerificationOrchestrator
from app.core.config import get_settings
from app.core.database import (
    get_dashboard_stats,
    get_db_status,
    get_last_db_error,
    get_record_count,
    get_verification_history,
    is_db_available,
    save_verification,
)
from app.schemas.verification import (
    DashboardStatsSchema,
    VerificationResultSchema,
    VerifyRequest,
)
from app.services.llm import validate_gemini_connection
from app import __version__

router = APIRouter()
orchestrator = VerificationOrchestrator()


@router.get("/health")
async def health_check():
    settings = get_settings()
    gemini = await validate_gemini_connection()
    db = get_db_status()
    record_count = await get_record_count() if is_db_available() else 0
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if is_db_available() else "unavailable",
        "database_host": db.get("host"),
        "database_error": get_last_db_error() if not is_db_available() else None,
        "stored_verifications": record_count,
        "gemini": gemini.get("status"),
        "gemini_model": settings.gemini_model if settings.gemini_api_key else None,
    }


@router.post("/verify", response_model=VerificationResultSchema)
async def verify_question(request: VerifyRequest):
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured. Add it to backend/.env",
        )
    try:
        result = await orchestrator.verify(request.question)
        await save_verification(result.model_dump(), request.session_id)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        err = str(e)
        if "RetryError" in err:
            err = "Gemini API quota exceeded or unavailable. Try again later or check your API key at https://aistudio.google.com"
        raise HTTPException(status_code=500, detail=f"Verification failed: {err}")


@router.post("/verify/stream")
async def verify_stream(request: VerifyRequest):
    settings = get_settings()
    if not settings.gemini_api_key:
        async def missing_key():
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "data": {"message": "GEMINI_API_KEY is not configured"},
                }),
            }
        return EventSourceResponse(missing_key())

    async def event_generator():
        try:
            async for event in orchestrator.verify_stream(request.question):
                yield {"event": "message", "data": json.dumps(event)}
                if event.get("type") == "complete":
                    await save_verification(event["data"], request.session_id)
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "data": {"message": str(e)}}),
            }

    return EventSourceResponse(event_generator())


@router.get("/dashboard/stats", response_model=DashboardStatsSchema)
async def dashboard_stats():
    return DashboardStatsSchema(**await get_dashboard_stats())


@router.get("/history")
async def verification_history(limit: int = 22):
    return await get_verification_history(limit)
