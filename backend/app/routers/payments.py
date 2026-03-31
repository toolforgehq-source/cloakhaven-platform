"""Stripe payment endpoints — $8 single lookup + $49/mo unlimited subscription."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.models.user import User
from app.models.purchased_report import PurchasedReport
from app.models.public_profile import PublicProfile
from app.middleware.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

REPORT_ACCESS_DAYS = 30  # Single lookup reports accessible for 30 days


class CreateCheckoutRequest(BaseModel):
    price_type: str  # "lookup" ($8 one-time) or "unlimited" ($49/mo)
    profile_id: Optional[str] = None  # Required for "lookup" — the report to unlock


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    stripe_customer_id: Optional[str]


class ReportAccessResponse(BaseModel):
    has_access: bool
    access_type: Optional[str] = None  # "purchased", "subscriber", or None
    expires_at: Optional[datetime] = None


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for single lookup or subscription."""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing not configured",
        )

    if request.price_type == "lookup":
        if not request.profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="profile_id is required for single lookup purchases",
            )
        # Verify the profile exists
        result = await db.execute(
            select(PublicProfile).where(PublicProfile.id == uuid.UUID(request.profile_id))
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

    price_config = {
        "lookup": {
            "mode": "payment",
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Cloak Haven - Single Report"},
                    "unit_amount": 800,  # $8.00
                },
                "quantity": 1,
            }],
        },
        "unlimited": {
            "mode": "subscription",
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Cloak Haven - Unlimited Reports"},
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
            detail="Invalid price type. Must be: lookup or unlimited",
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
        success_url=f"{settings.FRONTEND_URL}/search?payment=success&profile_id={request.profile_id or ''}",
        cancel_url=f"{settings.FRONTEND_URL}/search?payment=cancelled",
        metadata={
            "user_id": str(current_user.id),
            "price_type": request.price_type,
            "profile_id": request.profile_id or "",
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
        profile_id = session["metadata"].get("profile_id")

        if user_id:
            result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = result.scalar_one_or_none()
            if user:
                if price_type == "lookup" and profile_id:
                    # Upsert: extend expiration if already purchased
                    existing = await db.execute(
                        select(PurchasedReport).where(
                            PurchasedReport.user_id == uuid.UUID(user_id),
                            PurchasedReport.profile_id == uuid.UUID(profile_id),
                        )
                    )
                    existing_purchase = existing.scalar_one_or_none()
                    if existing_purchase:
                        existing_purchase.expires_at = datetime.utcnow() + timedelta(days=REPORT_ACCESS_DAYS)
                        existing_purchase.stripe_session_id = session.get("id")
                        existing_purchase.purchased_at = datetime.utcnow()
                    else:
                        purchased = PurchasedReport(
                            user_id=uuid.UUID(user_id),
                            profile_id=uuid.UUID(profile_id),
                            stripe_session_id=session.get("id"),
                            purchased_at=datetime.utcnow(),
                            expires_at=datetime.utcnow() + timedelta(days=REPORT_ACCESS_DAYS),
                        )
                        db.add(purchased)
                elif price_type == "unlimited":
                    user.subscription_tier = "subscriber"
                    user.subscription_status = "active"
                    user.stripe_subscription_id = session.get("subscription")
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
            user.stripe_subscription_id = None
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


@router.get("/report-access/{profile_id}", response_model=ReportAccessResponse)
async def check_report_access(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user has access to view a specific report."""
    # Subscribers have access to everything
    if current_user.subscription_tier == "subscriber" and current_user.subscription_status == "active":
        return ReportAccessResponse(
            has_access=True,
            access_type="subscriber",
        )

    # Check for a valid purchased report
    result = await db.execute(
        select(PurchasedReport).where(
            PurchasedReport.user_id == current_user.id,
            PurchasedReport.profile_id == profile_id,
            PurchasedReport.expires_at > datetime.utcnow(),
        )
    )
    purchase = result.scalar_one_or_none()
    if purchase:
        return ReportAccessResponse(
            has_access=True,
            access_type="purchased",
            expires_at=purchase.expires_at,
        )

    return ReportAccessResponse(has_access=False)
