"""ResiliChain AI - FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_db
from app.middleware.auth_context import AuthContextMiddleware
from app.middleware.exception_handlers import register_exception_handlers
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.timing import RequestTimingMiddleware
from app.utils.logger import configure_logging, get_logger

logger = get_logger("resilichain")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    configure_logging()
    logger.info(
        "Starting %s v%s (%s)",
        settings.PROJECT_NAME,
        __version__,
        settings.ENVIRONMENT,
    )
    if settings.AUTO_CREATE_TABLES:
        await init_db()
        logger.info("Database tables ensured (AUTO_CREATE_TABLES=true)")
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware. add_middleware() prepends, so the LAST one added runs
    # FIRST on each request: CORS -> rate limit -> auth ctx -> logging -> timing.
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_origins_list != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Health"])
    async def root() -> dict:
        """Service metadata."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        """Liveness probe."""
        return {"status": "ok"}

    return app


app = create_app()
