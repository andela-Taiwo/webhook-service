"""Webhook endpoint for processing incoming webhook events."""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.v1.schemas.event import Event
from src.core.config import settings
from src.core.logging import get_logger
from src.db.deps import get_session
from src.services.webhook_idempotency import WebhookIdempotencyService
from src.services.webhook_processor import WebhookProcessor, WebhookProcessingError
from src.services.webhook_security import WebhookSecurityService

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)

# Initialize services
security_service = WebhookSecurityService(secret_key=settings.webhook_secret_key)
idempotency_service = WebhookIdempotencyService()
processor = WebhookProcessor()


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    event: Event,
    session: AsyncSession = Depends(get_session),
    x_webhook_signature: str | None = Header(None, alias=settings.webhook_signature_header),
) -> Dict[str, Any]:
    """
    Receive and process incoming webhook events.

    Security: Verifies HMAC signature
    Idempotency: Prevents duplicate processing
    Processing: Routes events to appropriate handlers

    Args:
        request: FastAPI request object
        event: Webhook event payload
        session: Database session
        x_webhook_signature: Webhook signature header

    Returns:
        Processing result

    Raises:
        HTTPException: For security or processing failures
    """
    event_id = event.id
    event_type = event.type

    logger.info(f"Received webhook event {event_id} of type {event_type}")

    # Step 1: Verify webhook signature
    try:
        body = await request.body()
        payload_str = body.decode("utf-8")

        if not security_service.verify_signature(payload_str, x_webhook_signature):
            logger.warning(f"Invalid signature for event {event_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signature verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature verification failed",
        )

    # Step 2: Check for duplicate event (idempotency)
    try:
        is_duplicate = await idempotency_service.is_duplicate(
            session=session, event_id=event_id
        )

        if is_duplicate:
            logger.info(f"Duplicate event {event_id} detected, skipping processing")
            return {
                "status": "success",
                "message": "Event already processed (idempotent)",
                "event_id": event_id,
            }

        # Create idempotency record
        await idempotency_service.create_event(
            session=session,
            event_id=event_id,
            event_type=event_type,
            payload=event.model_dump(),
        )
        await session.commit()

    except Exception as e:
        await session.rollback()
        logger.error(f"Idempotency check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check event idempotency",
        )

    # Step 3: Mark event as processing
    try:
        await idempotency_service.mark_processing(session=session, event_id=event_id)
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to mark event as processing: {str(e)}")

    # Step 4: Process the webhook event
    try:
        result = await processor.process_event(
            session=session, event=event.model_dump()
        )

        # Mark as completed
        await idempotency_service.mark_completed(session=session, event_id=event_id)
        await session.commit()

        logger.info(f"Successfully processed event {event_id}")

        return {
            "status": "success",
            "event_id": event_id,
            "event_type": event_type,
            "result": result,
        }

    except WebhookProcessingError as e:
        # Mark as failed
        await session.rollback()
        await idempotency_service.mark_failed(
            session=session, event_id=event_id, error_message=str(e)
        )
        await session.commit()

        logger.error(f"Webhook processing failed for {event_id}: {str(e)}")

        # Check if should retry
        should_retry = await idempotency_service.should_retry(
            session=session, event_id=event_id
        )

        if should_retry:
            # TODO: Queue for retry (implement with RabbitMQ)
            logger.info(f"Event {event_id} queued for retry")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}",
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error processing event {event_id}: {str(e)}")

        try:
            await idempotency_service.mark_failed(
                session=session, event_id=event_id, error_message=str(e)
            )
            await session.commit()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook",
        )
