"""Webhook event processor for routing events to appropriate handlers."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.logging import get_logger
from src.db.models import (
    InvoiceModel,
    PaymentModel,
    RefundModel,
    SubscriptionModel,
)

logger = get_logger(__name__)


class WebhookProcessingError(Exception):
    """Raised when webhook event processing fails."""
    # pass


class WebhookProcessor:
    """
    Process webhook events and route them to appropriate handlers.

    Responsibilities:
    - Route events to correct handler based on event type
    - Extract and transform event data
    - Create appropriate database records
    - Handle errors gracefully
    """

    def __init__(self):
        """Initialize webhook processor with event type handlers."""
        self._handlers: dict[str, Callable] = {
            "payment_intent.succeeded": self._handle_payment_succeeded,
            "invoice.created": self._handle_invoice_created,
            "invoice.payment_succeeded": self._handle_invoice_created,
            "charge.refunded": self._handle_refund_created,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_created,
        }

    async def process_event(
        self, session: AsyncSession, event: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process webhook event and route to appropriate handler.

        Args:
            session: Database session
            event: Webhook event data

        Returns:
            Processing result dictionary

        Raises:
            WebhookProcessingError: If processing fails
        """
        event_type = event.get("type")
        event_id = event.get("id")

        logger.info(f"Processing webhook event {event_id} of type {event_type}")

        # Get handler for event type
        handler = self._get_handler(event_type)

        if handler is None:
            logger.warning(f"No handler found for event type: {event_type}")
            return {
                "status": "ignored",
                "event_id": event_id,
                "event_type": event_type,
                "message": f"Unsupported event type: {event_type}",
            }

        try:
            # Call handler to process event
            result = await handler(session, event)

            # Commit the transaction
            await session.commit()

            logger.info(f"Successfully processed event {event_id}")

            return {
                "status": "success",
                "event_id": event_id,
                "event_type": event_type,
                "result": result,
            }

        except Exception as e:
            # Rollback transaction on error
            await session.rollback()
            # logger.error(f"Error processing event {event_id}: {str(e)}")
            logger.error(f"Error processing event {event_id}: {e!s}")
            raise WebhookProcessingError(
                f"Failed to process event {event_id}: {e!s}"
            ) from e

    def _get_handler(self, event_type: str) -> Callable| None:
        """
        Get handler function for event type.

        Args:
            event_type: Type of webhook event

        Returns:
            Handler function or None if not supported
        """
        return self._handlers.get(event_type)

    async def _handle_payment_succeeded(
        self, session: AsyncSession, event: dict[str, Any]
    ) -> PaymentModel:
        """
        Handle payment_intent.succeeded event.

        Args:
            session: Database session
            event: Webhook event data

        Returns:
            Created PaymentModel

        Raises:
            WebhookProcessingError: If required fields are missing
        """
        data = event.get("data", {}).get("object", {})

        try:
            payment = PaymentModel(
                user_name=self._extract_customer_email(data),
                amount=self._convert_amount_from_cents(data["amount"]),
                payment_method=data.get("payment_method", "unknown"),
                payment_date=datetime.now(UTC),
            )

            session.add(payment)
            await session.flush()

            logger.info(f"Created payment record for {payment.user_name}")
            return payment

        except KeyError as e:
            raise WebhookProcessingError(f"Missing required field: {e}") from e

    async def _handle_invoice_created(
        self, session: AsyncSession, event: dict[str, Any]
    ) -> InvoiceModel:
        """
        Handle invoice.created event.

        Args:
            session: Database session
            event: Webhook event data

        Returns:
            Created InvoiceModel

        Raises:
            WebhookProcessingError: If required fields are missing
        """
        data = event.get("data", {}).get("object", {})

        try:
            # Parse due date
            due_date_str = data.get("due_date")
            if due_date_str:
                if isinstance(due_date_str, str):
                    due_date = datetime.fromisoformat(
                        due_date_str.replace("Z", "+00:00")
                    )
                else:
                    # Unix timestamp
                    due_date = datetime.fromtimestamp(due_date_str, tz=UTC)
            else:
                due_date = datetime.now(UTC)

            invoice = InvoiceModel(
                user_name=self._extract_customer_email(data),
                invoice_number=data.get("invoice_number", data["id"]),
                amount_due=self._convert_amount_from_cents(data["amount_due"]),
                due_date=due_date,
                issued_date=datetime.now(UTC),
            )

            session.add(invoice)
            await session.flush()

            logger.info(f"Created invoice record {invoice.invoice_number}")
            return invoice

        except KeyError as e:
            raise WebhookProcessingError(f"Missing required field: {e}") from e

    async def _handle_refund_created(
        self, session: AsyncSession, event: dict[str, Any]
    ) -> RefundModel:
        """
        Handle charge.refunded event.

        Args:
            session: Database session
            event: Webhook event data

        Returns:
            Created RefundModel

        Raises:
            WebhookProcessingError: If required fields are missing
        """
        data = event.get("data", {}).get("object", {})

        try:
            refund = RefundModel(
                user_name=self._extract_customer_email(data),
                amount=self._convert_amount_from_cents(data["amount"]),
                refund_reason=data.get("reason", "no_reason_provided"),
                refund_date=datetime.now(UTC),
            )

            session.add(refund)
            await session.flush()

            logger.info(f"Created refund record for {refund.user_name}")
            return refund

        except KeyError as e:
            raise WebhookProcessingError(f"Missing required field: {e}") from e

    async def _handle_subscription_created(
        self, session: AsyncSession, event: dict[str, Any]
    ) -> SubscriptionModel:
        """
        Handle customer.subscription.created event.

        Args:
            session: Database session
            event: Webhook event data

        Returns:
            Created SubscriptionModel

        Raises:
            WebhookProcessingError: If required fields are missing
        """
        data = event.get("data", {}).get("object", {})

        try:
            # Extract monthly fee from plan
            plan = data.get("plan", {})
            monthly_fee = self._convert_amount_from_cents(plan.get("amount", 0))

            subscription = SubscriptionModel(
                user_name=self._extract_customer_email(data),
                monthly_fee=monthly_fee,
                subscription_date=datetime.now(UTC),
            )

            session.add(subscription)
            await session.flush()

            logger.info(f"Created subscription record for {subscription.user_name}")
            return subscription

        except KeyError as e:
            raise WebhookProcessingError(f"Missing required field: {e}") from e

    def _extract_customer_email(self, data: dict[str, Any]) -> str:
        """
        Extract customer email from event data.

        Args:
            data: Event object data

        Returns:
            Customer email address

        Raises:
            WebhookProcessingError: If email cannot be extracted
        """
        email = data.get("customer_email")

        if not email:
            # Try alternative fields
            customer = data.get("customer", {})
            if isinstance(customer, dict):
                email = customer.get("email")

        if not email:
            raise WebhookProcessingError("Customer email not found in event data")

        return email

    def _convert_amount_from_cents(self, amount_cents: int) -> float:
        """
        Convert amount from cents to dollars.

        Args:
            amount_cents: Amount in cents

        Returns:
            Amount in dollars
        """
        return round(amount_cents / 100, 2)
