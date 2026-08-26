"""Tests for webhook idempotency handling."""

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.webhook_event import WebhookEvent, WebhookEventStatus
from src.services.webhook_idempotency import WebhookIdempotencyService


class TestWebhookIdempotency:
    """Test webhook idempotency tracking and prevention of duplicate processing."""

    @pytest.fixture
    def idempotency_service(self):
        """Create idempotency service instance."""
        return WebhookIdempotencyService()

    @pytest.fixture
    def sample_event_data(self):
        """Create sample event data."""
        return {
            "event_id": "evt_test_123",
            "event_type": "payment_intent.succeeded",
            "payload": {
                "id": "evt_test_123",
                "type": "payment_intent.succeeded",
                "data": {"object": {"id": "pi_123", "amount": 1000}},
            },
        }

    @pytest.mark.asyncio
    async def test_create_event_record(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test creating a new webhook event record."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )

        assert event.event_id == sample_event_data["event_id"]
        assert event.event_type == sample_event_data["event_type"]
        assert event.status == WebhookEventStatus.PENDING
        assert event.retry_count == 0
        assert event.processed_at is None

    @pytest.mark.asyncio
    async def test_check_duplicate_event_not_exists(
        self, db_session: AsyncSession, idempotency_service
    ):
        """Test checking for duplicate when event doesn't exist."""
        is_duplicate = await idempotency_service.is_duplicate(
            session=db_session, event_id="evt_new_unique_123"
        )

        assert is_duplicate is False

    @pytest.mark.asyncio
    async def test_check_duplicate_event_exists(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test detecting duplicate event."""
        # Create initial event
        await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        # Check for duplicate
        is_duplicate = await idempotency_service.is_duplicate(
            session=db_session, event_id=sample_event_data["event_id"]
        )

        assert is_duplicate is True

    @pytest.mark.asyncio
    async def test_prevent_duplicate_processing(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test that attempting to create duplicate event fails."""
        # Create initial event
        await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        # Attempt to create duplicate should raise error or return None
        with pytest.raises(Exception):  # Database unique constraint violation
            await idempotency_service.create_event(
                session=db_session,
                event_id=sample_event_data["event_id"],
                event_type="different_type",
                payload={},
            )
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_mark_event_processing(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test marking event as processing."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        # Mark as processing
        updated = await idempotency_service.mark_processing(
            session=db_session, event_id=sample_event_data["event_id"]
        )

        assert updated is not None
        assert updated.status == WebhookEventStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_mark_event_completed(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test marking event as completed."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        # Mark as completed
        updated = await idempotency_service.mark_completed(
            session=db_session, event_id=sample_event_data["event_id"]
        )

        assert updated is not None
        assert updated.status == WebhookEventStatus.COMPLETED
        assert updated.processed_at is not None

    @pytest.mark.asyncio
    async def test_mark_event_failed(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test marking event as failed with error message."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        error_msg = "Database connection failed"

        # Mark as failed
        updated = await idempotency_service.mark_failed(
            session=db_session,
            event_id=sample_event_data["event_id"],
            error_message=error_msg,
        )

        assert updated is not None
        assert updated.status == WebhookEventStatus.FAILED
        assert updated.last_error == error_msg
        assert updated.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_count_increments(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test that retry count increments on failures."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        # Fail multiple times
        for i in range(3):
            updated = await idempotency_service.mark_failed(
                session=db_session,
                event_id=sample_event_data["event_id"],
                error_message=f"Attempt {i+1} failed",
            )
            await db_session.commit()
            assert updated.retry_count == i + 1

    @pytest.mark.asyncio
    async def test_should_retry_within_limit(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test that event should retry when under max retries."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        await db_session.commit()

        # Fail once
        await idempotency_service.mark_failed(
            session=db_session,
            event_id=sample_event_data["event_id"],
            error_message="First failure",
        )
        await db_session.commit()

        # Check should retry
        should_retry = await idempotency_service.should_retry(
            session=db_session, event_id=sample_event_data["event_id"]
        )

        assert should_retry is True

    @pytest.mark.asyncio
    async def test_should_not_retry_after_max_attempts(
        self, db_session: AsyncSession, idempotency_service, sample_event_data
    ):
        """Test that event should not retry after max attempts."""
        event = await idempotency_service.create_event(
            session=db_session,
            event_id=sample_event_data["event_id"],
            event_type=sample_event_data["event_type"],
            payload=sample_event_data["payload"],
        )
        event.max_retries = 3
        await db_session.commit()

        # Fail max times
        for _ in range(3):
            await idempotency_service.mark_failed(
                session=db_session,
                event_id=sample_event_data["event_id"],
                error_message="Failure",
            )
            await db_session.commit()

        # Check should not retry
        should_retry = await idempotency_service.should_retry(
            session=db_session, event_id=sample_event_data["event_id"]
        )

        assert should_retry is False
