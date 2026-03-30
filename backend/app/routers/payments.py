"""Stripe payment endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.middleware.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class CreateCheckoutRequest(BaseModel):
    price_type: str  # "audit" ($19 one-time), "subscriber" ($9/mo), "employer" ($49/mo)


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    stripe_customer_id: Optional[str]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session."""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing not configured",
        )

    price_config = {
        "audit": {
            "mode": "payment",
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Cloak Haven - Full Audit"},
                    "unit_amount": 1900,  # $19.00
                },
                "quantity": 1,
            }],
        },
        "subscriber": {
            "mode": "subscription",
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Cloak Haven - Monthly Monitoring"},
                    "unit_amount": 900,  # $9.00/mo
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
        },
        "employer": {
            "mode": "subscription",
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Cloak Haven - Employer Tier"},
                    "unit_amount": 4900,  # $49.00/mo
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
        },
    }

    if request.price_type not in price_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid price type. Must be: audit, subscriber, or employer",
        )

    config = price_config[request.price_type]

    # Create or get Stripe customer
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.full_name,
            metadata={"user_id": str(current_user.id)},
        )
        current_user.stripe_customer_id = customer.id
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=current_user.stripe_customer_id,
        mode=config["mode"],
        line_items=config["line_items"],
        success_url=f"{settings.FRONTEND_URL}/dashboard?payment=success",
        cancel_url=f"{settings.FRONTEND_URL}/pricing?payment=cancelled",
        metadata={
            "user_id": str(current_user.id),
            "price_type": request.price_type,
        },
    )

    return CheckoutResponse(
        checkout_url=session.url,
        session_id=session.id,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        price_type = session["metadata"].get("price_type")

        if user_id:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                if price_type == "audit":
                    user.subscription_tier = "audit"
                    user.subscription_status = "active"
                elif price_type == "subscriber":
                    user.subscription_tier = "subscriber"
                    user.subscription_status = "active"
                elif price_type == "employer":
                    user.subscription_tier = "employer"
                    user.subscription_status = "active"
                await db.commit()

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]

        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.subscription_tier = "free"
            user.subscription_status = "cancelled"
            await db.commit()

    return {"received": True}


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
):
    return SubscriptionResponse(
        tier=current_user.subscription_tier,
        status=current_user.subscription_status,
        stripe_customer_id=current_user.stripe_customer_id,
    )
