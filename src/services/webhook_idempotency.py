"""Webhook idempotency service for preventing duplicate processing."""

from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.webhook_event import WebhookEvent, WebhookEventStatus


class WebhookIdempotencyService:
    """
    Service for ensuring webhook idempotency.

    Responsibilities:
    - Track all webhook events by unique event_id
    - Prevent duplicate processing of same event
    - Track processing status and retry attempts
    - Provide audit trail of all webhook events
    """

    async def create_event(
        self,
        session: AsyncSession,
        event_id: str,
        event_type: str,
        payload: dict,
        max_retries: int = 3,
    ) -> WebhookEvent:
        """
        Create a new webhook event record.

        Args:
            session: Database session
            event_id: Unique event identifier from webhook provider
            event_type: Type of webhook event
            payload: Full webhook payload
            max_retries: Maximum number of retry attempts

        Returns:
            Created webhook event

        Raises:
            IntegrityError: If event_id already exists (duplicate event)
        """
        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status=WebhookEventStatus.PENDING,
            max_retries=max_retries,
        )

        session.add(event)
        await session.flush()  # Flush to catch unique constraint violations
        return event

    async def is_duplicate(self, session: AsyncSession, event_id: str) -> bool:
        """
        Check if event has already been received.

        Args:
            session: Database session
            event_id: Event identifier to check

        Returns:
            True if event exists, False otherwise
        """
        event = await self.get_event(session, event_id)
        return event is not None

    async def get_event(
        self, session: AsyncSession, event_id: str
    ) -> WebhookEvent | None:
        """
        Get webhook event by ID.

        Args:
            session: Database session
            event_id: Event identifier

        Returns:
            WebhookEvent if found, None otherwise
        """
        statement = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        result = await session.exec(statement)
        return result.first()

    async def mark_processing(
        self, session: AsyncSession, event_id: str
    ) -> WebhookEvent | None:
        """
        Mark event as currently being processed.

        Args:
            session: Database session
            event_id: Event identifier

        Returns:
            Updated event or None if not found
        """
        event = await self.get_event(session, event_id)
        if event:
            event.status = WebhookEventStatus.PROCESSING
            event.updated_at = datetime.now(UTC)
            session.add(event)
            await session.flush()
        return event

    async def mark_completed(
        self, session: AsyncSession, event_id: str
    ) -> WebhookEvent | None:
        """
        Mark event as successfully completed.

        Args:
            session: Database session
            event_id: Event identifier

        Returns:
            Updated event or None if not found
        """
        event = await self.get_event(session, event_id)
        if event:
            event.status = WebhookEventStatus.COMPLETED
            event.processed_at = datetime.now(UTC)
            event.updated_at = datetime.now(UTC)
            session.add(event)
            await session.flush()
        return event

    async def mark_failed(
        self, session: AsyncSession, event_id: str, error_message: str
    ) -> WebhookEvent | None:
        """
        Mark event as failed and increment retry count.

        Args:
            session: Database session
            event_id: Event identifier
            error_message: Description of error

        Returns:
            Updated event or None if not found
        """
        event = await self.get_event(session, event_id)
        if event:
            event.status = WebhookEventStatus.FAILED
            event.last_error = error_message
            event.retry_count += 1
            event.updated_at = datetime.now(UTC)
            session.add(event)
            await session.flush()
        return event

    async def should_retry(self, session: AsyncSession, event_id: str) -> bool:
        """
        Determine if failed event should be retried.

        Args:
            session: Database session
            event_id: Event identifier

        Returns:
            True if retry should be attempted, False otherwise
        """
        event = await self.get_event(session, event_id)
        if not event:
            return False

        return event.retry_count < event.max_retries
