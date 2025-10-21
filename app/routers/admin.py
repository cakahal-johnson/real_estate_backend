from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.core.security import require_admin
from sqlalchemy import func

router = APIRouter(prefix="/admin", tags=["Admin"])


# --- USERS ---
@router.get("/users")
def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return db.query(models.User).all()


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted"}


# --- LISTINGS ---
@router.get("/listings")
def list_all_listings(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return db.query(models.Listing).all()


@router.patch("/listings/{listing_id}/approve")
def approve_listing(listing_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    listing = db.query(models.Listing).get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    # you could add a “status” column (approved/pending)
    setattr(listing, "status", "approved")
    db.commit()
    return {"message": f"Listing {listing_id} approved"}


@router.delete("/listings/{listing_id}")
def delete_listing_admin(listing_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    listing = db.query(models.Listing).get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.delete(listing)
    db.commit()
    return {"message": f"Listing {listing_id} deleted"}


# --- ORDERS ---
@router.get("/orders")
def list_orders(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return db.query(models.Order).all()


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, status_update: dict, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status_update.get("status", order.status)
    db.commit()
    return {"message": f"Order {order_id} status updated to {order.status}"}


# --- CHATS ---
@router.get("/chats")
def list_chats(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return db.query(models.ChatMessage).all()


@router.get("/revenue-summary")
def revenue_summary(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    total_orders = db.query(func.count(models.Order.id)).scalar()
    total_revenue = db.query(func.sum(models.Order.amount)).scalar()
    completed = db.query(func.count(models.Order.id)).filter(models.Order.status == "completed").scalar()

    return {
        "total_orders": total_orders or 0,
        "completed_orders": completed or 0,
        "total_revenue": total_revenue or 0.0,
    }
