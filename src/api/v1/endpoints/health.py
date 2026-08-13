from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readiness() -> dict:
    return {"status": "ok"}
