"""FastAPI application factory and ASGI entrypoint.

Run locally with: uvicorn webhook_service.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import configure_logging, get_logger
from src.middleware.request_context import RequestContextMiddleware

configure_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("service_starting", environment=settings.environment)
    yield
    logger.info("service_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # health checks live at the root, not under /api/v1, so probes/load
    # balancers don't need to know about API versioning
    from src.api.v1.endpoints import health

    app.include_router(health.router)

    return app


app = create_app()
