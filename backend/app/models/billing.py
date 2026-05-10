import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

PLAN_FREE = "free"
PLAN_PRO = "pro"

STATUS_INACTIVE = "inactive"
STATUS_ACTIVE = "active"
STATUS_PAST_DUE = "past_due"
STATUS_CANCELED = "canceled"
STATUS_TRIALING = "trialing"


class UserBilling(Base):
    __tablename__ = "user_billing"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default=PLAN_FREE)
    subscription_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_INACTIVE
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
