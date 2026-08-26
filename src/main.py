"""
FastAPI application entry point for webhook service.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints import health, webhook
from src.api.v1.router import api_router
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import configure_logging, get_logger
from src.middleware.request_context import RequestContextMiddleware

configure_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting webhook service",
        extra={
            "environment": settings.environment,
            "log_level": settings.log_level,
        },
    )

    yield

    # Shutdown
    logger.info("Shutting down webhook service")


# Create FastAPI application
app = FastAPI(
    title="Webhook Service",
    description="Production-grade webhook processing service with security, idempotency, and retry handling",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request context middleware
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

# Include routers
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["Health"])
app.include_router(webhook.router, prefix=settings.api_v1_prefix, tags=["Webhooks"])

# app.include_router(api_router, prefix=settings.api_v1_prefix)
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "webhook-service",
        "version": "1.0.0",
        "environment": settings.environment,
    }
