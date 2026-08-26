"""Webhook endpoint for processing incoming webhook events."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.v1.schemas.event import Event
from src.core.config import settings
from src.core.logging import get_logger
from src.db.deps import get_session
from src.services.webhook_idempotency import WebhookIdempotencyService
from src.services.webhook_processor import WebhookProcessingError, WebhookProcessor
from src.services.webhook_security import WebhookSecurityService

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)

# Initialize services
security_service = WebhookSecurityService(secret_key=settings.webhook_secret_key)
idempotency_service = WebhookIdempotencyService()
processor = WebhookProcessor()


async def get_raw_body(request: Request) -> bytes:
    """
    Extract raw body from request before FastAPI consumes it.

    Args:
        request: FastAPI request object

    Returns:
        Raw request body as bytes
    """
    return await request.body()


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_webhook_signature: str | None = Header(
        None, alias=settings.webhook_signature_header
    ),
) -> dict[str, Any]:
    """
    Receive and process incoming webhook events.

    Security: Verifies HMAC signature
    Idempotency: Prevents duplicate processing
    Processing: Routes events to appropriate handlers

    Args:
        request: FastAPI request object
        session: Database session
        x_webhook_signature: Webhook signature header

    Returns:
        Processing result

    Raises:
        HTTPException: For security or processing failures
    """
    # Step 1: Get raw body for signature verification
    try:
        body = await request.body()
        payload_str = body.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to read request body: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read request body",
        )

    # Step 2: Verify webhook signature BEFORE parsing
    try:
        if not security_service.verify_signature(payload_str, x_webhook_signature):
            logger.warning("Invalid signature for webhook")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signature verification failed: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature verification failed",
        )

    # Step 3: Parse the event payload
    try:
        import json
        event_data = json.loads(payload_str)
        event = Event(**event_data)
    except Exception as e:
        logger.error(f"Failed to parse event payload: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event payload",
        )

    event_id = event.id
    event_type = event.type

    logger.info(f"Received webhook event {event_id} of type {event_type}")

    # Step 4: Check for duplicate event (idempotency)
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
        logger.error(f"Idempotency check failed: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check event idempotency",
        )

    # Step 5: Mark event as processing
    try:
        await idempotency_service.mark_processing(session=session, event_id=event_id)
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to mark event as processing: {e!s}")

    # Step 6: Process the webhook event
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

        logger.error(f"Webhook processing failed for {event_id}: {e!s}")

        # Check if should retry
        should_retry = await idempotency_service.should_retry(
            session=session, event_id=event_id
        )

        if should_retry:
            # TODO: Queue for retry (implement with RabbitMQ)
            logger.info(f"Event {event_id} queued for retry")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {e!s}",
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error processing event {event_id}: {e!s}")

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
