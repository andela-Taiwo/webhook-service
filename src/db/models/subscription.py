from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

class Subscription(BaseModel):
    user_name: str
    monthly_fee: float
    subscription_date: datetime

class UserBase(SQLModel):
    email: EmailStr = Field(index=True, unique=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    full_name: str | None = Field(default=None, index=True)

class SubscriptionModel(SQLModel, table=True):
    __tablename__ = "subscriptions"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_name: str = Field(index=True)
    monthly_fee: float
    subscription_date: datetime = Field(default_factory=datetime.utcnow, sa_column=DateTime(timezone=True))