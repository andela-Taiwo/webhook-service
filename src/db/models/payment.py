import uuid
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone

class PaymentModel(SQLModel, table=True):
    __tablename__ = "payments"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_name: str = Field(index=True)
    amount: float
    payment_method: str
    payment_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvoiceModel(SQLModel, table=True):
    __tablename__ = "invoices"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_name: str = Field(index=True)
    invoice_number: str = Field(index=True, unique=True)
    amount_due: float
    due_date: datetime
    issued_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RefundModel(SQLModel, table=True):
    __tablename__ = "refunds"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_name: str = Field(index=True)
    amount: float
    refund_reason: str
    refund_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))