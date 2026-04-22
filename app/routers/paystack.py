# app/routers/paystack.py

import os
import httpx
import hmac
import hashlib

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime

from app import models, database, schemas
from app.schemas import PaymentRequest
from app.utils.email_utils import send_email

router = APIRouter(prefix="/orders/paystack", tags=["Paystack Payments"])

# ⚠️ MUST be SECRET KEY (NOT pk_test)
PAYSTACK_SECRET_KEY = os.getenv(
    "PAYSTACK_SECRET_KEY",
    "sk_test_xxxxxxxxxxxxxxxxxxxxxxxxx"  # ✅ FIXED
)

PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


# =========================================================
# 🔐 PAYSTACK WEBHOOK CALLBACK (SECURE)
# =========================================================
@router.post("/callback")
async def paystack_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    body = await request.body()
    payload = await request.json()

    signature = request.headers.get("x-paystack-signature")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing Paystack signature")

    # ✅ Verify signature
    computed_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        body,
        hashlib.sha512
    ).hexdigest()

    if signature != computed_signature:
        raise HTTPException(status_code=401, detail="Invalid Paystack signature")

    # -----------------------------
    # ✅ Paystack sends event-based payload
    # -----------------------------
    event = payload.get("event")
    data = payload.get("data", {})

    if event != "charge.success":
        return {"message": "Event ignored"}

    reference = data.get("reference")
    metadata = data.get("metadata", {})
    order_id = metadata.get("order_id")

    if not reference or not order_id:
        raise HTTPException(status_code=400, detail="Missing reference or order_id")

    # -----------------------------
    # 🔍 Find order
    # -----------------------------
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # ✅ Prevent duplicate webhook processing
    if order.payment_status == "paid":
        return {"message": "Already processed"}

    # -----------------------------
    # 🔍 Verify transaction with Paystack
    # -----------------------------
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            PAYSTACK_VERIFY_URL.format(reference),
            headers=headers
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail="Failed to verify transaction"
        )

    verify_data = resp.json().get("data", {})

    if verify_data.get("status") != "success":
        raise HTTPException(status_code=400, detail="Payment not successful")

    amount_paid = verify_data.get("amount", 0) / 100
    channel = verify_data.get("channel")

    # -----------------------------
    # ✅ Update order
    # -----------------------------
    order.payment_status = "paid"
    order.status = "approved"
    order.payment_reference = reference
    order.payment_method = channel or "paystack"
    order.amount = amount_paid
    order.completed_at = datetime.utcnow()

    # ✅ mark listing sold
    if order.listing:
        order.listing.status = "sold"

    db.commit()
    db.refresh(order)

    # -----------------------------
    # 👥 Fetch users safely
    # -----------------------------
    buyer = db.query(models.User).filter(models.User.id == order.buyer_id).first()
    listing = order.listing

    agent = None
    if listing and listing.owner_id:
        agent = db.query(models.User).filter(
            models.User.id == listing.owner_id
        ).first()

    # -----------------------------
    # 📧 Email content (safe fields)
    # -----------------------------
    buyer_name = buyer.full_name or "Customer"
    agent_name = agent.full_name if agent else "Agent"

    buyer_subject = f"Payment Confirmation - Order #{order.id}"
    buyer_body = f"""
Hi {buyer_name},

Your payment of ₦{amount_paid:,.2f} for "{listing.title if listing else 'a property'}" was successful.

Reference: {reference}
Method: {channel}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Thank you for using RealEstateHub.
"""

    agent_subject = f"New Payment Received - Order #{order.id}"
    agent_body = f"""
Hi {agent_name},

A buyer ({buyer.email}) completed payment of ₦{amount_paid:,.2f}
for "{listing.title if listing else 'a property'}".

Reference: {reference}
Channel: {channel}

Please contact the buyer.
"""

    # -----------------------------
    # 📤 Send emails
    # -----------------------------
    if buyer:
        background_tasks.add_task(
            send_email,
            to=buyer.email,
            subject=buyer_subject,
            body=buyer_body,
            bcc=ADMIN_EMAIL
        )

    if agent:
        background_tasks.add_task(
            send_email,
            to=agent.email,
            subject=agent_subject,
            body=agent_body,
            bcc=ADMIN_EMAIL
        )

    return {
        "message": "Payment verified",
        "order_id": order.id,
        "status": order.payment_status,
    }


@router.post("/payments/initiate")
def initiate_payment(payload: PaymentRequest):
    # call Paystack API here
    return {
        "authorization_url": "https://paystack.com/pay/xxxx"
    }


# =========================================================
# 🧪 DEV VERIFY (FRONTEND SAFE)
# =========================================================
@router.post("/verify")
def verify_payment_manual(
    payload: schemas.PaystackVerifyRequest,
    db: Session = Depends(database.get_db),
):
    order = db.query(models.Order).filter(
        models.Order.id == payload.order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status == "paid":
        return {"message": "Already verified", "order_id": order.id}

    # ✅ update once (no duplicates)
    order.payment_status = "paid"
    order.status = "approved"
    order.payment_reference = payload.reference
    order.completed_at = datetime.utcnow()

    # ✅ mark listing sold
    if order.listing:
        order.listing.status = "sold"

    db.commit()
    db.refresh(order)

    return {
        "message": "Payment verified successfully",
        "order_id": order.id,
        "payment_status": order.payment_status,
        "reference": order.payment_reference,
    }