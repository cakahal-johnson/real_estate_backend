# app/routers/orders.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    BackgroundTasks,
    Query,
    Path,
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


# -------------------------------------------------------------------
# 🧩 ROLE GUARD
# -------------------------------------------------------------------
def require_role(user: models.User, allowed_roles: list[str]):
    """Restrict endpoint access based on allowed user roles."""
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied — requires one of: {', '.join(allowed_roles)}",
        )


# -------------------------------------------------------------------
# 🛒 CREATE NEW ORDER
# -------------------------------------------------------------------
@router.post("/", response_model=schemas.OrderResponse)
def create_order(
        order_data: schemas.OrderCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """
    Buyer places a new order for a property listing.
    Sends background email to the agent.
    """
    require_role(current_user, ["buyer"])

    listing = db.query(models.Listing).filter(
        models.Listing.id == order_data.listing_id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Prevent duplicate orders for same listing
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

    # Create new order
    new_order = models.Order(
        buyer_id=current_user.id,
        listing_id=order_data.listing_id,
        status="pending",
        payment_status="unpaid",
        created_at=datetime.utcnow(),
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Background email to agent
    if listing.owner and listing.owner.email:
        background_tasks.add_task(
            send_verification_email,
            to_email=listing.owner.email,
            subject="New Order Notification",
            body=f"""
            Hi {listing.owner.full_name or 'Agent'},

            A new order was placed for your listing:
            🏡 {listing.title}

            Buyer: {current_user.full_name} ({current_user.email})
            Listing ID: {listing.id}
            Order ID: {new_order.id}

            Please log in to your agent dashboard for details.
            — RealEstateHub Team
            """,
        )

    return new_order


# -------------------------------------------------------------------
# 📦 BUYER — VIEW MY ORDERS (with pagination)
# -------------------------------------------------------------------
@router.get("/my")
def get_my_orders(
        page: int = Query(1, ge=1),
        page_size: int = Query(6, ge=1, le=50),
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Return paginated orders for the logged-in buyer."""
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

    for order in orders:
        order.listing = db.query(models.Listing).filter(
            models.Listing.id == order.listing_id
        ).first()

    has_more = page * page_size < total
    return {"orders": orders, "hasMore": has_more}


# -------------------------------------------------------------------
# 💼 AGENT/ADMIN — VIEW SALES ORDERS
# -------------------------------------------------------------------
@router.get("/sales", response_model=List[schemas.OrderResponse])
def get_my_sales(
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Agent or Admin can view orders related to their listings."""
    require_role(current_user, ["agent", "admin"])

    orders = (
        db.query(models.Order)
            .join(models.Listing)
            .filter(models.Listing.owner_id == current_user.id)
            .order_by(models.Order.created_at.desc())
            .all()
    )
    return orders


# -------------------------------------------------------------------
# 🧾 UPDATE ORDER STATUS
# -------------------------------------------------------------------
@router.patch("/{order_id}", response_model=schemas.OrderResponse)
def update_order_status(
        order_id: int = Path(..., gt=0),
        status_update: schemas.OrderUpdate = ...,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Agent or Admin can update an order’s status."""
    require_role(current_user, ["agent", "admin"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order


# -------------------------------------------------------------------
# 🧾 ADMIN — VIEW ALL ORDERS
# -------------------------------------------------------------------
@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Admin-only endpoint to fetch all orders."""
    require_role(current_user, ["admin"])
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()


# -------------------------------------------------------------------
# 💳 SIMULATED PAYMENT (Buyers)
# -------------------------------------------------------------------
@router.post("/{order_id}/pay", response_model=schemas.PaymentResponse)
def simulate_payment(
        order_id: int = Path(..., gt=0),
        payment: schemas.PaymentRequest = ...,
        background_tasks: BackgroundTasks = None,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """
    Simulate successful payment for an order.
    After success, send background email notifications to buyer & agent.
    """
    require_role(current_user, ["buyer"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="This order is already paid.")

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

    # Send background email notification to both Buyer & Agent
    listing = db.query(models.Listing).filter(models.Listing.id == order.listing_id).first()
    if background_tasks and listing and listing.owner:
        agent_email = listing.owner.email
        buyer_email = current_user.email

        # Notify Agent
        background_tasks.add_task(
            send_verification_email,
            to_email=agent_email,
            subject="Payment Received - Your Listing",
            body=f"""
            Hi {listing.owner.full_name or 'Agent'},

            Your property listing '{listing.title}' has received a payment.
            Buyer: {current_user.full_name} ({current_user.email})
            Order ID: {order.id}
            Amount: ${order.amount}

            Please proceed to upload property documents.
            — RealEstateHub Team
            """,
        )

        # Notify Buyer
        background_tasks.add_task(
            send_verification_email,
            to_email=buyer_email,
            subject="Payment Confirmation - RealEstateHub",
            body=f"""
            Hi {current_user.full_name or 'Buyer'},

            Your payment for '{listing.title}' has been received successfully.
            Order ID: {order.id}
            Amount: ${order.amount}
            Reference: {order.payment_reference}

            Our agent will reach out to you shortly.
            — RealEstateHub Team
            """,
        )

    return schemas.PaymentResponse(
        order_id=order.id,
        payment_status=order.payment_status,
        payment_reference=order.payment_reference,
        amount=order.amount,
        timestamp=datetime.utcnow(),
    )


# -------------------------------------------------------------------
# ✅ MARK ORDER AS COMPLETED
# -------------------------------------------------------------------
@router.post("/{order_id}/complete", response_model=schemas.OrderResponse)
def complete_order(
        order_id: int = Path(..., gt=0),
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Mark order as completed (Agent/Admin only)."""
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


# -------------------------------------------------------------------
# 📊 SALES SUMMARY
# -------------------------------------------------------------------
@router.get("/sales/summary")
def get_sales_summary(
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Get total sales count and revenue for current agent/admin."""
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


# -------------------------------------------------------------------
# 📂 GET APPROVED DOCUMENTS FOR ORDER
# -------------------------------------------------------------------
@router.get("/{order_id}/documents")
def get_order_documents(
        order_id: int,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
):
    """Fetch approved documents for a given order (Buyer/Admin only)."""
    require_role(current_user, ["buyer", "admin"])

    docs = (
        db.query(models.DocumentSubmission)
            .filter(models.DocumentSubmission.order_id == order_id)
            .filter(models.DocumentSubmission.status == "approved")
            .all()
    )
    if not docs:
        raise HTTPException(status_code=404, detail="No approved documents found")

    return [
        {
            "file_url": d.file_url,
            "remarks": d.remarks,
            "date": d.created_at,
        }
        for d in docs
    ]
