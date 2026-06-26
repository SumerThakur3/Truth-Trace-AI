"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import __version__
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import init_db, is_db_available
from app.core.logging import setup_logging, logger
from app.services.llm import validate_gemini_connection
from app.services.rag import init_vectorstore

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.debug)

    await init_db()
    await init_vectorstore()

    gemini_status = await validate_gemini_connection()
    db_status = "connected" if is_db_available() else "unavailable"

    logger.info(
        "truthtrace_started",
        version=__version__,
        database=db_status,
        gemini=gemini_status.get("status"),
    )

    if gemini_status.get("status") == "error":
        logger.warning("gemini_startup_warning", message=gemini_status.get("message"))
    elif gemini_status.get("status") == "missing_key":
        logger.warning("gemini_key_missing")

    yield
    logger.info("truthtrace_shutdown")


app = FastAPI(
    title="TruthTrace AI",
    description="Enterprise-grade fact verification and trust analysis API",
    version=__version__,
    lifespan=lifespan,
)

settings = get_settings()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {
        "name": "TruthTrace AI",
        "tagline": "Every answer with proof.",
        "version": __version__,
        "docs": "/docs",
        "database": "connected" if is_db_available() else "unavailable",
    }
