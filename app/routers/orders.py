# app/routers/orders.py
from fastapi import (
    APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Path
)
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from sqlalchemy import func

from app import models, schemas, database
from app.core.security import get_current_user
from app.core.email import send_verification_email

router = APIRouter(prefix="/orders", tags=["Orders"])


# ✅ Helper: Role guard
def require_role(user: models.User, allowed_roles: list[str]):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied — requires one of: {', '.join(allowed_roles)}"
        )


# ✅ POST — Buyer places an order
@router.post("/", response_model=schemas.OrderResponse)
def create_order(
    order_data: schemas.OrderCreate,  # 👈 Body JSON
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["buyer"])

    listing = db.query(models.Listing).filter(
        models.Listing.id == order_data.listing_id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing_order = (
        db.query(models.Order)
        .filter(
            models.Order.buyer_id == current_user.id,
            models.Order.listing_id == order_data.listing_id,
        )
        .first()
    )
    if existing_order:
        raise HTTPException(status_code=400, detail="You already placed this order")

    new_order = models.Order(buyer_id=current_user.id, listing_id=order_data.listing_id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # background email to agent
    if listing.owner and listing.owner.email:
        background_tasks.add_task(
            send_verification_email,
            listing.owner.email,
            subject="New Order Notification",
            body=f"""
            Hi {listing.owner.full_name or 'Agent'},

            A new order was placed on your listing: {listing.title}
            Buyer: {current_user.full_name} ({current_user.email})
            Listing ID: {listing.id}
            Order ID: {new_order.id}

            Log in to your dashboard for details.
            — RealEstateHub Team
            """,
        )

    return new_order


# ✅ GET — Buyer views their own orders with pagination
@router.get("/my")
def get_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(6, ge=1, le=50),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["buyer"])

    total = (
        db.query(models.Order)
        .filter(models.Order.buyer_id == current_user.id)
        .count()
    )

    orders = (
        db.query(models.Order)
        .filter(models.Order.buyer_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Attach related listing info for each order
    result = []
    for order in orders:
        listing = db.query(models.Listing).filter(models.Listing.id == order.listing_id).first()
        order.listing = listing
        result.append(order)

    has_more = page * page_size < total
    return {"orders": result, "hasMore": has_more}


# ✅ GET — Agent/Admin view of orders for their listings
@router.get("/sales", response_model=List[schemas.OrderResponse])
def get_my_sales(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["agent", "admin"])

    orders = (
        db.query(models.Order)
        .join(models.Listing)
        .filter(models.Listing.owner_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return orders


# ✅ PATCH — Agent/Admin updates order status
@router.patch("/{order_id}", response_model=schemas.OrderResponse)
def update_order_status(
    order_id: int = Path(..., gt=0),
    status_update: schemas.OrderUpdate = ...,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["agent", "admin"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order


# ✅ GET — Admin-only view of all orders
@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["admin"])
    return db.query(models.Order).all()


# ✅ POST — Simulated Payment
@router.post("/{order_id}/pay", response_model=schemas.PaymentResponse)
def simulate_payment(
    order_id: int = Path(..., gt=0),
    payment: schemas.PaymentRequest = ...,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["buyer"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.payment_status == "paid":
        raise HTTPException(
            status_code=400, detail="This order has already been paid."
        )

    if payment.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    # Simulate payment success
    order.payment_method = payment.payment_method
    order.amount = payment.amount
    order.payment_status = "paid"
    order.status = "approved"
    order.payment_reference = f"PAY-{uuid.uuid4().hex[:10]}"
    order.completed_at = None

    db.commit()
    db.refresh(order)

    return schemas.PaymentResponse(
        order_id=order.id,
        payment_status=order.payment_status,
        payment_reference=order.payment_reference,
        amount=order.amount,
        timestamp=datetime.utcnow(),
    )


# ✅ POST — Mark order as completed
@router.post("/{order_id}/complete", response_model=schemas.OrderResponse)
def complete_order(
    order_id: int = Path(..., gt=0),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["agent", "admin"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "approved" or order.payment_status != "paid":
        raise HTTPException(status_code=400, detail="Order not eligible for completion")

    order.status = "completed"
    order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


# ✅ GET — Sales summary (revenue)
@router.get("/sales/summary")
def get_sales_summary(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["agent", "admin"])

    summary = (
        db.query(
            func.count(models.Order.id).label("total_orders"),
            func.sum(models.Order.amount).label("total_revenue"),
        )
        .join(models.Listing)
        .filter(models.Listing.owner_id == current_user.id)
        .filter(models.Order.payment_status == "paid")
        .one()
    )

    return {
        "total_orders": summary.total_orders or 0,
        "total_revenue": summary.total_revenue or 0.0,
    }
