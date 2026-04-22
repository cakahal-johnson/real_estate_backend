# app/routers/cart.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/cart", tags=["Cart"])


# -----------------------------
# ➕ ADD TO CART (MATCH FRONTEND)
# -----------------------------
@router.post("")
def add_to_cart(
    payload: schemas.CartCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    item = db.query(models.CartItem).filter_by(
        user_id=user.id,
        listing_id=payload.listing_id
    ).first()

    if item:
        item.quantity += 1
    else:
        item = models.CartItem(
            user_id=user.id,
            listing_id=payload.listing_id,
            quantity=1
        )
        db.add(item)

    db.commit()
    db.refresh(item)

    return {"message": "added", "item_id": item.id}


# -----------------------------
# 📦 GET CART (WITH LISTING DATA)
# -----------------------------
@router.get("")
def get_cart(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    items = (
        db.query(models.CartItem)
        .options(joinedload(models.CartItem.listing))
        .filter_by(user_id=user.id)
        .all()
    )

    # ✅ SAFE SERIALIZATION
    result = []
    total_quantity = 0
    total_price = 0

    for item in items:
        listing = item.listing

        price = listing.price if listing else 0
        quantity = item.quantity or 0

        total_quantity += quantity
        total_price += price * quantity

        result.append({
            "id": item.id,
            "quantity": quantity,
            "listing": {
                "id": listing.id if listing else None,
                "title": listing.title if listing else "",
                "price": price,
                "main_image": listing.main_image if listing else None,
                "location": listing.location if listing else None,
            }
        })

    return {
        "items": result,
        "total": total_quantity,        # for badge
        "subtotal": total_price        # for UI
    }


# -----------------------------
# ➖ REMOVE / DECREASE ITEM
# -----------------------------
@router.delete("/{item_id}")
def remove_from_cart(
    item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    item = db.query(models.CartItem).filter_by(
        id=item_id,
        user_id=user.id
    ).first()

    if not item:
        raise HTTPException(404, "Item not found")

    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.delete(item)

    db.commit()

    return {"message": "updated"}