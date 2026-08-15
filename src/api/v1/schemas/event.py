
from typing import Any, Dict
from pydantic import BaseModel


class Event(BaseModel):
    """Schema for Stripe webhook event payload."""

    id: str
    type: str
    data: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_1234567890",
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "id": "pi_1234567890",
                        "amount": 7777,
                        "currency": "eur",
                        "customer_email": "customer@example.com",
                        "lines": {"data": [{"invoice": "INV123456"}]},
                    }
                },
            }
        }