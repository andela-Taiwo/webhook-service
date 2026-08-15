"""Webhook event model for idempotency and tracking."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column as SAColumn, DateTime
from sqlmodel import Column, Field, JSON, SQLModel


class WebhookEventStatus(str, Enum):
    """Status of webhook event processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WebhookEvent(SQLModel, table=True):
    """
    Webhook event for idempotency tracking and audit trail.

    This model ensures:
    - Idempotency: Same event_id won't be processed twice
    - Audit trail: Track all webhook attempts
    - Retry tracking: Count failures and retry attempts
    """

    __tablename__ = "webhook_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    event_id: str = Field(index=True, unique=True)  # External webhook event ID
    event_type: str = Field(index=True)  # Type of webhook event
    payload: dict = Field(sa_column=Column(JSON))  # Full webhook payload
    status: WebhookEventStatus = Field(default=WebhookEventStatus.PENDING, index=True)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    last_error: Optional[str] = None
    processed_at: Optional[datetime] = Field(
        default=None, sa_column=SAColumn(DateTime(timezone=True))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=SAColumn(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=SAColumn(DateTime(timezone=True)),
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "event_id": "evt_1234567890",
                "event_type": "payment_intent.succeeded",
                "payload": {"data": {"object": {"id": "pi_123", "amount": 1000}}},
                "status": "pending",
            }
        }
