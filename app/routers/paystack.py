# app/routers/paystack.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app import models, database
from app.core.security import get_current_user
from app.utils.email_utils import send_email  # ✅ import your reusable email sender

router = APIRouter(prefix="/orders/paystack", tags=["Paystack Payments"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "pk_test_483997e17a8ad6468cc2edefb6132ea78babbf76")
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


@router.post("/callback")
async def paystack_callback(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    ✅ Verifies a Paystack payment and notifies buyer + agent.
    """
    reference = payload.get("reference")
    order_id = payload.get("order_id")

    if not reference or not order_id:
        raise HTTPException(status_code=400, detail="Missing payment reference or order ID")

    # --- Verify order existence ---
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to verify this order")

    # Skip if already paid
    if order.payment_status == "paid":
        return {"message": "Order already marked as paid"}

    # --- Verify Paystack transaction ---
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(PAYSTACK_VERIFY_URL.format(reference), headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to verify payment")

    data = resp.json()
    status_text = data.get("data", {}).get("status")
    amount_paid = data.get("data", {}).get("amount", 0) / 100
    channel = data.get("data", {}).get("channel")
    customer_email = data.get("data", {}).get("customer", {}).get("email")

    if status_text != "success":
        raise HTTPException(status_code=400, detail="Payment not successful")

    # --- Update Order ---
    order.payment_status = "paid"
    order.status = "approved"
    order.payment_reference = reference
    order.payment_method = channel or "paystack"
    order.amount = amount_paid
    order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    # --- Fetch related info for emails ---
    buyer = db.query(models.User).filter(models.User.id == order.buyer_id).first()
    listing = order.listing
    agent = (
        db.query(models.User)
        .filter(models.User.id == listing.owner_id)
        .first()
        if listing and listing.owner_id
        else None
    )

    # --- Compose email contents ---
    buyer_subject = f"Payment Confirmation for Order #{order.id}"
    buyer_body = f"""
    Hi {buyer.name},

    ✅ Your payment of ₦{amount_paid:,.2f} for "{listing.title if listing else 'a property'}" has been confirmed successfully.

    Transaction Reference: {reference}
    Payment Method: {channel}
    Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

    You can now proceed to communicate with the agent for next steps.

    Thank you for using RealEstateHub.
    """

    agent_subject = f"New Property Payment Received - Order #{order.id}"
    agent_body = f"""
    Hi {agent.name if agent else 'Agent'},

    A buyer ({buyer.email}) has successfully completed a payment of ₦{amount_paid:,.2f}
    for your property "{listing.title if listing else 'a property'}".

    Transaction Reference: {reference}
    Payment Channel: {channel}

    Please review the order details and contact the buyer for completion.

    - RealEstateHub System
    """

    # --- Background send emails ---
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
        "message": "✅ Payment verified and notifications sent",
        "order_id": order.id,
        "amount": order.amount,
        "channel": order.payment_method,
        "reference": order.payment_reference,
        "status": order.payment_status,
    }
