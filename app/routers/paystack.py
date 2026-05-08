# app/routers/paystack.py
import httpx
import hmac
import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from app import models, database, schemas
from app.core.security import get_current_user
from app.schemas import PaymentRequest
from app.utils.email_utils import send_email
from app.core.config import settings

router = APIRouter(prefix="/orders/paystack", tags=["Paystack Payments"])


# ================================
# 🔐 CONFIG
# ================================
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
ADMIN_EMAIL = settings.ADMIN_EMAIL

if not PAYSTACK_SECRET_KEY:
    raise Exception("PAYSTACK_SECRET_KEY is missing")

PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"


# =========================================================
# 🔐 PAYSTACK WEBHOOK CALLBACK
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
        raise HTTPException(status_code=401, detail="Missing signature")

    # verify signature
    computed = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        body,
        hashlib.sha512
    ).hexdigest()

    if computed != signature:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # ================================
    # EVENT CHECK
    # ================================
    event = payload.get("event")
    data = payload.get("data", {})

    if event != "charge.success":
        return {"message": "ignored"}

    reference = data.get("reference")
    metadata = data.get("metadata", {})

    # =========================================================
    # 🔥 NEW: checkout_ref SUPPORT (MULTI ORDER FLOW)
    # =========================================================
    checkout_ref = metadata.get("checkout_ref")
    order_id = metadata.get("order_id")

    if not reference:
        raise HTTPException(status_code=400, detail="Missing reference")

    # ================================
    # FIND ORDERS
    # ================================
    orders = []

    if checkout_ref:
        orders = db.query(models.Order).filter(
            models.Order.checkout_ref == checkout_ref
        ).all()

        if not orders:
            raise HTTPException(status_code=404, detail="Orders not found")

    elif order_id:
        order = db.query(models.Order).filter(
            models.Order.id == order_id
        ).first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        orders = [order]

    else:
        raise HTTPException(
            status_code=400,
            detail="Missing checkout_ref or order_id"
        )

    # ================================
    # VERIFY WITH PAYSTACK
    # ================================
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            PAYSTACK_VERIFY_URL.format(reference),
            headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Verification failed")

    verify_data = resp.json().get("data", {})

    if verify_data.get("status") != "success":
        raise HTTPException(status_code=400, detail="Payment not successful")

    amount_paid = verify_data.get("amount", 0) / 100
    channel = verify_data.get("channel")

    # ================================
    # UPDATE ALL ORDERS
    # ================================
    for order in orders:

        if order.payment_status == "paid":
            continue

        order.payment_status = "paid"
        order.status = "approved"
        order.payment_reference = reference
        order.payment_method = channel or "paystack"
        order.amount = amount_paid
        order.completed_at = datetime.utcnow()

        if order.listing:
            order.listing.status = "sold"

    db.commit()

    first_order = orders[0]

    # ================================
    # USERS
    # ================================
    buyer = db.query(models.User).filter(
        models.User.id == first_order.buyer_id
    ).first()

    listing = first_order.listing

    agent = None
    if listing and listing.owner_id:
        agent = db.query(models.User).filter(
            models.User.id == listing.owner_id
        ).first()

    # ================================
    # EMAILS
    # ================================
    buyer_name = buyer.full_name or "Customer"
    agent_name = agent.full_name if agent else "Agent"

    buyer_subject = f"Payment Successful - Order(s) Confirmed"
    buyer_body = f"""
Hi {buyer_name},

Your payment of ₦{amount_paid:,.2f} was successful.

Reference: {reference}
Method: {channel}
Time: {datetime.utcnow()}

You have {len(orders)} order(s) confirmed.
"""

    agent_subject = "New Payment Received"
    agent_body = f"""
Hi {agent_name},

A buyer has completed payment for {len(orders)} order(s).

Reference: {reference}
Channel: {channel}
"""

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
        "orders": [o.id for o in orders],
        "status": "paid"
    }


# =========================================================
# 💳 INITIATE PAYMENT (UPDATED FOR checkout_ref)
# =========================================================
@router.post("/payments/initiate")
async def initiate_payment(
    payload: PaymentRequest,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(get_current_user),
):
    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    if not user.email:
        raise HTTPException(status_code=400, detail="User email missing")

    data = {
        "email": user.email,
        "amount": int(payload.amount * 100),

        "metadata": {
            "checkout_ref": payload.checkout_ref,
            "order_ids": payload.order_ids
        },

        "callback_url": "http://localhost:3000/checkout/success"
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=data, headers=headers)

    response = res.json()

    if not response.get("status"):
        raise HTTPException(
            status_code=400,
            detail=response.get("message", "Payment initialization failed")
        )

    reference = response["data"]["reference"]

    # ✅ FIX: attach reference AFTER response exists
    if payload.order_ids:
        db.query(models.Order).filter(
            models.Order.id.in_(payload.order_ids)
        ).update(
            {"payment_reference": reference},
            synchronize_session=False
        )

        db.commit()

    return {
        "authorization_url": response["data"]["authorization_url"],
        "access_code": response["data"]["access_code"],
        "reference": reference
    }


# =========================================================
# 🔎 VERIFY PAYMENT BY REFERENCE (CHECKOUT FLOW)
# =========================================================
@router.get("/verify/{reference}")
def verify_by_reference(
    reference: str,
    db: Session = Depends(database.get_db),
):
    orders = db.query(models.Order).filter(
        models.Order.payment_reference == reference
    ).all()

    # ✅ DO NOT FAIL HARD
    if not orders:
        return {
            "status": "processing",
            "orders": [],
            "message": "Payment is still being processed"
        }

    return {
        "status": "paid",
        "orders": [o.id for o in orders]
    }


# =========================================================
# 🧪 MANUAL VERIFY (DEV)
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

    order.payment_status = "paid"
    order.status = "approved"
    order.payment_reference = payload.reference
    order.completed_at = datetime.utcnow()

    if order.listing:
        order.listing.status = "sold"

    db.commit()
    db.refresh(order)

    return {
        "message": "Payment verified",
        "order_id": order.id,
        "status": order.payment_status
    }
