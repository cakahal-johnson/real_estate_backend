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
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
import uuid
from sqlalchemy import func

from fastapi.responses import StreamingResponse
from app.utils.invoice import generate_invoice_pdf

# ✅ FIXED IMPORTS
from app import models, schemas
from app.database import get_db
from app.core.security import get_current_user
from app.core.email import send_verification_email
from app.schemas import PaginatedOrdersResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


# -------------------------------------------------------------------
# 🧩 ROLE GUARD
# -------------------------------------------------------------------
def require_role(user: models.User, allowed_roles: list[str]):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied — requires one of: {', '.join(allowed_roles)}",
        )


# -------------------------------------------------------------------
# 🛒 CREATE ORDER FROM CART (FIXED)
# -------------------------------------------------------------------
@router.post("/from-cart")
def create_order_from_cart(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        cart_items = db.query(models.CartItem).filter_by(user_id=user.id).all()

        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        created_orders = []

        # ✅ GENERATE checkout_ref ONCE
        checkout_ref = str(uuid.uuid4())

        for item in cart_items:
            listing = db.query(models.Listing).filter_by(id=item.listing_id).first()
            if not listing:
                continue

            order = models.Order(
                buyer_id=user.id,
                listing_id=item.listing_id,
                status="pending",
                payment_status="unpaid",
                amount=listing.price,
                checkout_ref=checkout_ref,  # ✅ FIXED
            )

            db.add(order)
            created_orders.append(order)

            db.delete(item)

        db.commit()

        if not created_orders:
            raise HTTPException(status_code=400, detail="No valid orders created")

        return {
            "checkout_ref": checkout_ref,  # ✅ now valid
            "order_ids": [o.id for o in created_orders],
            "count": len(created_orders),
            "total_amount": sum(o.amount for o in created_orders)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# 🛒 CREATE NEW ORDER
# -------------------------------------------------------------------
@router.post("/", response_model=schemas.OrderResponse)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),  # ✅ FIXED
    current_user: models.User = Depends(get_current_user),
):
    require_role(current_user, ["buyer"])

    listing = db.query(models.Listing).filter(
        models.Listing.id == order.listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot order your own listing")

    if listing.status == "sold":
        raise HTTPException(
            status_code=400,
            detail="This property has already been sold."
        )

    existing = db.query(models.Order).filter(
        models.Order.buyer_id == current_user.id,
        models.Order.listing_id == order.listing_id,
        models.Order.status.in_(["pending", "approved"])
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Order already exists")

    new_order = models.Order(
        buyer_id=current_user.id,
        listing_id=order.listing_id,
        status="pending",
        payment_status="unpaid",
        amount=listing.price
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    new_order.listing = listing

    return new_order


# -------------------------------------------------------------------
# 🛒 GET ORDERS (PAGINATED)
# -------------------------------------------------------------------
@router.get("", response_model=PaginatedOrdersResponse)
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(6, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):

    base_query = db.query(models.Order).options(
        joinedload(models.Order.listing)
    )

    if current_user.role == "buyer":
        base_query = base_query.filter(
            models.Order.buyer_id == current_user.id
        )

    elif current_user.role == "agent":
        base_query = base_query.join(models.Order.listing).filter(
            models.Listing.owner_id == current_user.id
        )

    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    total = base_query.count()

    orders = (
        base_query
        .order_by(models.Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "orders": orders,
        "hasMore": page * page_size < total,
        "total": total,
    }


@router.get("/{order_id}/receipt")
def get_invoice(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    pdf_buffer = generate_invoice_pdf(order)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{order.id}.pdf"
        }
    )
