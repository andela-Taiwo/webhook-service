from fastapi import APIRouter

router = APIRouter(tags=["webhook"])


@router.post("/webhook")
async def webhook():
    return {"status": "ok", "message": "called webhook"}
