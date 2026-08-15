from fastapi import APIRouter, Depends, HTTPException, status, Request
from src.core.logging import get_logger
from src.db.deps import get_session
from src.db.models.payment import PaymentModel, InvoiceModel, RefundModel
from src.api.v1.schemas.event import Event
router = APIRouter(tags=["webhooks"])

logger = get_logger(__name__)

@router.post("/webhooks")
async def webhook(event: Event, session=Depends(get_session)):
    db_payment = PaymentModel()
    #[TODO] validate the webhook payload here
    #[TODO] process the webhook payload here

    logger.info("Webhook called with body: %s", body)

    return {"status": "ok", "message": "called webhook"}
