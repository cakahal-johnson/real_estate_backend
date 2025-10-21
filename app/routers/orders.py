from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, database
# ✅ already implemented from your JWT utils
from app.core.security import get_current_user

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


# ✅ POST — Buyer places an order for a listing
@router.post("/", response_model=schemas.OrderResponse)
def create_order(
    listing_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    # buyers only
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

    # create
    new_order = models.Order(buyer_id=current_user.id, listing_id=listing_id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
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
