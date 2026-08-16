"""Tests for webhook event processing and routing."""

import pytest
from datetime import datetime, timezone
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import (
    PaymentModel,
    InvoiceModel,
    RefundModel,
    SubscriptionModel,
    WebhookEvent,
)
from src.services.webhook_processor import WebhookProcessor, WebhookProcessingError


class TestWebhookProcessor:
    """Test webhook event processing and routing to appropriate tables."""

    @pytest.fixture
    def processor(self):
        """Create webhook processor instance."""
        return WebhookProcessor()

    @pytest.fixture
    def payment_succeeded_event(self):
        """Sample payment succeeded event."""
        return {
            "id": "evt_payment_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123456",
                    "amount": 5000,  # $50.00 in cents
                    "currency": "usd",
                    "customer_email": "customer@example.com",
                    "payment_method": "card",
                }
            },
        }

    @pytest.fixture
    def invoice_created_event(self):
        """Sample invoice created event."""
        return {
            "id": "evt_invoice_123",
            "type": "invoice.created",
            "data": {
                "object": {
                    "id": "in_123456",
                    "invoice_number": "INV-2026-001",
                    "customer_email": "customer@example.com",
                    "amount_due": 7500,  # $75.00 in cents
                    "due_date": "2026-09-15T00:00:00Z",
                }
            },
        }

    @pytest.fixture
    def refund_created_event(self):
        """Sample refund created event."""
        return {
            "id": "evt_refund_123",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "re_123456",
                    "amount": 2500,  # $25.00 in cents
                    "customer_email": "customer@example.com",
                    "reason": "requested_by_customer",
                }
            },
        }

    @pytest.fixture
    def subscription_created_event(self):
        """Sample subscription created event."""
        return {
            "id": "evt_subscription_123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_123456",
                    "customer_email": "customer@example.com",
                    "plan": {"amount": 1999},  # $19.99 in cents
                }
            },
        }

    @pytest.mark.asyncio
    async def test_process_payment_succeeded(
        self, db_session: AsyncSession, processor, payment_succeeded_event
    ):
        """Test processing payment_intent.succeeded event creates PaymentModel."""
        result = await processor.process_event(
            session=db_session, event=payment_succeeded_event
        )

        assert result is not None
        assert result["status"] == "success"
        assert result["event_type"] == "payment_intent.succeeded"

        # Verify payment was created in database
        statement = select(PaymentModel)
        payments = await db_session.exec(statement)
        payment = payments.first()

        assert payment is not None
        assert payment.user_name == "customer@example.com"
        assert payment.amount == 50.00  # Converted from cents
        assert payment.payment_method == "card"

    @pytest.mark.asyncio
    async def test_process_invoice_created(
        self, db_session: AsyncSession, processor, invoice_created_event
    ):
        """Test processing invoice.created event creates InvoiceModel."""
        result = await processor.process_event(
            session=db_session, event=invoice_created_event
        )

        assert result is not None
        assert result["status"] == "success"

        # Verify invoice was created
        statement = select(InvoiceModel)
        invoices = await db_session.exec(statement)
        invoice = invoices.first()

        assert invoice is not None
        assert invoice.user_name == "customer@example.com"
        assert invoice.invoice_number == "INV-2026-001"
        assert invoice.amount_due == 75.00

    @pytest.mark.asyncio
    async def test_process_refund_created(
        self, db_session: AsyncSession, processor, refund_created_event
    ):
        """Test processing charge.refunded event creates RefundModel."""
        result = await processor.process_event(
            session=db_session, event=refund_created_event
        )

        assert result is not None
        assert result["status"] == "success"

        # Verify refund was created
        statement = select(RefundModel)
        refunds = await db_session.exec(statement)
        refund = refunds.first()

        assert refund is not None
        assert refund.user_name == "customer@example.com"
        assert refund.amount == 25.00
        assert refund.refund_reason == "requested_by_customer"

    @pytest.mark.asyncio
    async def test_process_subscription_created(
        self, db_session: AsyncSession, processor, subscription_created_event
    ):
        """Test processing customer.subscription.created event creates SubscriptionModel."""
        result = await processor.process_event(
            session=db_session, event=subscription_created_event
        )

        assert result is not None
        assert result["status"] == "success"

        # Verify subscription was created
        statement = select(SubscriptionModel)
        subscriptions = await db_session.exec(statement)
        subscription = subscriptions.first()

        assert subscription is not None
        assert subscription.user_name == "customer@example.com"
        assert subscription.monthly_fee == 19.99

    @pytest.mark.asyncio
    async def test_process_unsupported_event_type(
        self, db_session: AsyncSession, processor
    ):
        """Test that unsupported event types are handled gracefully."""
        unsupported_event = {
            "id": "evt_unsupported_123",
            "type": "unsupported.event.type",
            "data": {"object": {}},
        }

        result = await processor.process_event(
            session=db_session, event=unsupported_event
        )

        assert result is not None
        assert result["status"] == "ignored"
        assert "unsupported" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_malformed_event_data(
        self, db_session: AsyncSession, processor
    ):
        """Test that malformed event data raises appropriate error."""
        malformed_event = {
            "id": "evt_malformed_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    # Missing required fields
                    "id": "pi_123",
                }
            },
        }

        with pytest.raises(WebhookProcessingError) as exc_info:
            await processor.process_event(session=db_session, event=malformed_event)

        error_msg = str(exc_info.value).lower()
        assert "missing" in error_msg or "invalid" in error_msg or "not found" in error_msg

    @pytest.mark.asyncio
    async def test_get_handler_for_event_type(self, processor):
        """Test that correct handler is returned for each event type."""
        # Test payment handler
        handler = processor._get_handler("payment_intent.succeeded")
        assert handler is not None

        # Test invoice handler
        handler = processor._get_handler("invoice.created")
        assert handler is not None

        # Test refund handler
        handler = processor._get_handler("charge.refunded")
        assert handler is not None

        # Test subscription handler
        handler = processor._get_handler("customer.subscription.created")
        assert handler is not None

        # Test unknown handler
        handler = processor._get_handler("unknown.event")
        assert handler is None

    @pytest.mark.asyncio
    async def test_amount_conversion_from_cents(self, processor):
        """Test that amounts are correctly converted from cents to dollars."""
        assert processor._convert_amount_from_cents(5000) == 50.00
        assert processor._convert_amount_from_cents(1999) == 19.99
        assert processor._convert_amount_from_cents(100) == 1.00
        assert processor._convert_amount_from_cents(0) == 0.00

    @pytest.mark.asyncio
    async def test_extract_customer_email(self, processor, payment_succeeded_event):
        """Test customer email extraction from event data."""
        # Extract from the nested object
        email = processor._extract_customer_email(payment_succeeded_event["data"]["object"])
        assert email == "customer@example.com"

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(
        self, db_session: AsyncSession, processor
    ):
        """Test that database transaction is rolled back on processing error."""
        # Create event that will fail during processing
        failing_event = {
            "id": "evt_failing_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_fail",
                    "amount": "invalid",  # Invalid type will cause error
                    "customer_email": "test@example.com",
                }
            },
        }

        with pytest.raises(Exception):
            await processor.process_event(session=db_session, event=failing_event)

        # Verify no partial data was saved
        statement = select(PaymentModel)
        payments = await db_session.exec(statement)
        payment = payments.first()

        assert payment is None
