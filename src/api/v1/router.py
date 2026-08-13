from fastapi import APIRouter

from .endpoints import health, webhook

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(webhook.router)
