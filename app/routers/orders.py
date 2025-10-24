from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from sqlalchemy import func

from app import models, schemas, database
from app.core.security import get_current_user
from app.core.email import send_verification_email  # temporary reuse

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


# ✅ Helper: Role guard
def require_role(user: models.User, allowed_roles: list[str]):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied — requires one of: {', '.join(allowed_roles)}"
        )


# ✅ POST — Buyer places an order for a listing (with background email)
@router.post("/", response_model=schemas.OrderResponse)
def create_order(
    listing_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_role(current_user, ["buyer"])

    # check if listing exists
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # prevent duplicate order
    existing_order = (
        db.query(models.Order)
        .filter(models.Order.buyer_id == current_user.id, models.Order.listing_id == listing_id)
        .first()
    )
    if existing_order:
        raise HTTPException(status_code=400, detail="You already placed an order for this listing")

    # create order
    new_order = models.Order(buyer_id=current_user.id, listing_id=listing_id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # ✅ Notify agent via background email
    if listing.owner and listing.owner.email:
        background_tasks.add_task(
            send_verification_email,  # reuse same helper
            listing.owner.email,
            subject="New order placed on your listing",
            body=f"""
            Hello {listing.owner.name},

            A new order was placed on your listing: {listing.title}.

            Buyer: {current_user.name} ({current_user.email})
            Listing ID: {listing.id}
            Order ID: {new_order.id}

            Please log in to your dashboard to review the order.

            — RealEstateHub Team
            """
        )

    return new_order


# ✅ GET — Buyer views their own orders
@router.get("/my", response_model=List[schemas.OrderResponse])
def get_my_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_role(current_user, ["buyer"])
    orders = db.query(models.Order).filter(models.Order.buyer_id == current_user.id).all()
    return orders


# ✅ GET — Agent/Admin views orders on their listings
@router.get("/sales", response_model=List[schemas.OrderResponse])
def get_my_sales(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_role(current_user, ["agent", "admin"])
    orders = (
        db.query(models.Order)
        .join(models.Listing)
        .filter(models.Listing.owner_id == current_user.id)
        .all()
    )
    return orders


# ✅ PATCH — Admin or agent updates order status
@router.patch("/{order_id}", response_model=schemas.OrderResponse)
def update_order_status(
    order_id: int,
    status_update: schemas.OrderUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_role(current_user, ["agent", "admin"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order


# ✅ GET — Admin-only: All orders overview
@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])
    return db.query(models.Order).all()


# router for payment + completion
@router.post("/{order_id}/pay", response_model=schemas.PaymentResponse)
def simulate_payment(
    order_id: int,
    payment: schemas.PaymentRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # buyers only
    require_role(current_user, ["buyer"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    # simulate payment success
    order.payment_method = payment.payment_method
    order.amount = payment.amount
    order.payment_status = "paid"
    order.status = "approved"
    order.payment_reference = f"PAY-{uuid.uuid4().hex[:10]}"
    db.commit()
    db.refresh(order)

    return schemas.PaymentResponse(
        order_id=order.id,
        payment_status=order.payment_status,
        payment_reference=order.payment_reference,
        amount=order.amount,
        timestamp=datetime.utcnow()
    )


@router.post("/{order_id}/complete", response_model=schemas.OrderResponse)
def complete_order(
    order_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Agents/Admin mark an order as completed after payment.
    """
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


# Add Revenue Tracking (Admin/Agent view)
@router.get("/sales/summary")
def get_sales_summary(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_role(current_user, ["agent", "admin"])

    query = (
        db.query(
            func.count(models.Order.id).label("total_orders"),
            func.sum(models.Order.amount).label("total_revenue"),
        )
        .join(models.Listing)
        .filter(models.Listing.owner_id == current_user.id)
        .filter(models.Order.payment_status == "paid")
    )
    result = query.one()
    return {
        "total_orders": result.total_orders or 0,
        "total_revenue": result.total_revenue or 0.0,
    }
