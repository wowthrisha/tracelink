"""Stripe billing router.

Endpoints:
  GET  /api/billing/status        — current user's plan and subscription state
  POST /api/billing/checkout      — create a Stripe Checkout Session (→ redirect URL)
  POST /api/billing/portal        — create a Stripe Customer Portal session (→ URL)
  POST /api/billing/webhook       — Stripe webhook handler (public, HMAC-verified)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth import get_current_user
from app.config import settings
from app.models.billing import (
    UserBilling, PLAN_FREE, PLAN_PRO,
    STATUS_INACTIVE, STATUS_CANCELED, STATUS_PAST_DUE,
)

_log = logging.getLogger("securedoc.billing")
router = APIRouter(prefix="/api/billing", tags=["billing"])


# ── helpers ────────────────────────────────────────────────────────────────

async def _get_or_create_billing(db: AsyncSession, user_id: uuid.UUID) -> UserBilling:
    result = await db.execute(select(UserBilling).where(UserBilling.user_id == user_id))
    billing = result.scalar_one_or_none()
    if not billing:
        billing = UserBilling(user_id=user_id)
        db.add(billing)
        await db.commit()
        await db.refresh(billing)
    return billing


def _billing_dict(billing: UserBilling) -> dict:
    return {
        "plan": billing.plan,
        "subscription_status": billing.subscription_status,
        "stripe_customer_id": billing.stripe_customer_id,
        "current_period_end": (
            billing.current_period_end.isoformat() if billing.current_period_end else None
        ),
        "billing_enabled": settings.billing_enabled,
    }


def _require_stripe():
    if not settings.billing_enabled:
        raise HTTPException(
            status_code=503,
            detail="Billing is not configured. Set STRIPE_SECRET_KEY in environment.",
        )
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


# ── routes ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def billing_status(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the current user's plan and Stripe subscription state."""
    user_id = uuid.UUID(user["user_id"])
    billing = await _get_or_create_billing(db, user_id)
    return _billing_dict(billing)


@router.post("/checkout")
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for upgrading to Pro. Returns {url}."""
    stripe = _require_stripe()
    if not settings.stripe_price_id_pro:
        raise HTTPException(status_code=503, detail="STRIPE_PRICE_ID_PRO not configured.")

    user_id = uuid.UUID(user["user_id"])
    billing = await _get_or_create_billing(db, user_id)

    # Create or reuse Stripe customer
    customer_id = billing.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.get("email", ""),
            metadata={"user_id": str(user_id)},
        )
        customer_id = customer.id
        billing.stripe_customer_id = customer_id
        await db.commit()

    base_url = settings.app_public_base_url.rstrip("/")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id_pro, "quantity": 1}],
        success_url=f"{base_url}/static/SecureDoc.html?billing=success",
        cancel_url=f"{base_url}/static/SecureDoc.html?billing=cancel",
        metadata={"user_id": str(user_id)},
        allow_promotion_codes=True,
    )
    return {"url": session.url}


@router.post("/portal")
async def billing_portal(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session. Returns {url}."""
    stripe = _require_stripe()

    user_id = uuid.UUID(user["user_id"])
    billing = await _get_or_create_billing(db, user_id)

    if not billing.stripe_customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account found. Upgrade to Pro first."
        )

    base_url = settings.app_public_base_url.rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=billing.stripe_customer_id,
        return_url=f"{base_url}/static/SecureDoc.html?screen=billing",
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """Stripe webhook handler. Must be registered in the Stripe dashboard.
    Verifies payload with STRIPE_WEBHOOK_SECRET before processing.
    """
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing not configured.")
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET not configured.")

    import stripe

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")
    except Exception as exc:
        _log.warning("Webhook parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook parse error.")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        await _handle_subscription_upsert(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)
    elif event_type == "checkout.session.completed":
        # subscription is handled by subscription.created; just log
        _log.info("Checkout completed: %s", data.get("id"))

    return {"received": True}


# ── webhook helpers ─────────────────────────────────────────────────────────

async def _handle_subscription_upsert(db: AsyncSession, sub: dict) -> None:
    customer_id = sub.get("customer")
    status = sub.get("status", STATUS_INACTIVE)
    sub_id = sub.get("id")
    period_end_ts = sub.get("current_period_end")
    period_end = (
        datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else None
    )

    result = await db.execute(
        select(UserBilling).where(UserBilling.stripe_customer_id == customer_id)
    )
    billing = result.scalar_one_or_none()
    if not billing:
        _log.warning("Webhook: no billing row for customer %s", customer_id)
        return

    billing.stripe_subscription_id = sub_id
    billing.subscription_status = status
    billing.current_period_end = period_end
    billing.plan = PLAN_PRO if status in ("active", "trialing") else PLAN_FREE
    await db.commit()
    _log.info("Subscription %s updated: plan=%s status=%s", sub_id, billing.plan, status)


async def _handle_payment_failed(db: AsyncSession, invoice: dict) -> None:
    """Mark a subscription as past_due immediately on the first payment failure.

    Without this handler, the user keeps Pro access during Stripe's retry window
    (which can be several days). Handling invoice.payment_failed lets us revoke
    Pro access immediately and redirect the user to update their payment method.
    """
    customer_id = invoice.get("customer")
    result = await db.execute(
        select(UserBilling).where(UserBilling.stripe_customer_id == customer_id)
    )
    billing = result.scalar_one_or_none()
    if not billing:
        _log.warning("Webhook payment_failed: no billing row for customer %s", customer_id)
        return

    billing.subscription_status = STATUS_PAST_DUE
    billing.plan = PLAN_FREE
    await db.commit()
    _log.info("Payment failed for customer %s — plan downgraded to free", customer_id)


async def _handle_subscription_deleted(db: AsyncSession, sub: dict) -> None:
    customer_id = sub.get("customer")
    result = await db.execute(
        select(UserBilling).where(UserBilling.stripe_customer_id == customer_id)
    )
    billing = result.scalar_one_or_none()
    if not billing:
        return

    billing.subscription_status = STATUS_CANCELED
    billing.plan = PLAN_FREE
    billing.current_period_end = None
    await db.commit()
    _log.info("Subscription canceled for customer %s", customer_id)
