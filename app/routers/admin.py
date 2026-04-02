# app/routers/admin.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models
from app.core.security import get_current_user, require_admin, require_role
import os

# Ensure document upload directory exists
os.makedirs("uploads/docs", exist_ok=True)

router = APIRouter(prefix="/admin", tags=["Admin"])

# -------------------------------------------------------------------
# 🧩 USERS MANAGEMENT
# -------------------------------------------------------------------
@router.get("/users", summary="List all users (Admin only)")
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    users = db.query(models.User).all()
    return users


@router.delete("/users/{user_id}", summary="Delete a user by ID")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted successfully."}


# -------------------------------------------------------------------
# 🏘 LISTINGS MANAGEMENT
# -------------------------------------------------------------------
@router.get("/listings", summary="List all property listings")
def list_all_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    listings = db.query(models.Listing).all()
    return listings


@router.patch("/listings/{listing_id}/approve", summary="Approve a listing")
def approve_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ Ensure status field exists in Listing model
    setattr(listing, "status", "approved")
    db.commit()
    db.refresh(listing)

    return {"message": f"Listing {listing_id} approved successfully."}


@router.delete("/listings/{listing_id}", summary="Delete a listing")
def delete_listing_admin(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    db.delete(listing)
    db.commit()
    return {"message": f"Listing {listing_id} deleted successfully."}


# -------------------------------------------------------------------
# 🧾 ORDERS MANAGEMENT
# -------------------------------------------------------------------
@router.get("/orders", summary="List all orders")
def list_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    orders = db.query(models.Order).all()
    return orders


@router.patch("/orders/{order_id}/status", summary="Update order status")
def update_order_status(
    order_id: int,
    status_update: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing status value")

    order.status = new_status
    db.commit()
    db.refresh(order)
    return {"message": f"Order {order_id} status updated to '{order.status}'."}


@router.patch("/orders/{order_id}/confirm-payment", summary="Confirm buyer payment manually")
def confirm_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.payment_status = "paid"
    order.status = "approved"
    db.commit()
    db.refresh(order)

    return {"message": f"Order #{order.id} payment confirmed by admin."}


# -------------------------------------------------------------------
# 💬 CHATS MANAGEMENT
# -------------------------------------------------------------------
@router.get("/chats", summary="List all chat messages")
def list_chats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    chats = db.query(models.ChatMessage).all()
    return chats


# -------------------------------------------------------------------
# 💰 REVENUE SUMMARY
# -------------------------------------------------------------------
@router.get("/revenue-summary", summary="Get platform revenue overview")
def revenue_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    total_orders = db.query(func.count(models.Order.id)).scalar() or 0
    total_revenue = db.query(func.sum(models.Order.amount)).scalar() or 0.0
    completed_orders = (
        db.query(func.count(models.Order.id))
        .filter(models.Order.status == "completed")
        .scalar()
        or 0
    )

    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "total_revenue": total_revenue,
    }


# -------------------------------------------------------------------
# 📄 DOCUMENT SUBMISSION & REVIEW
# -------------------------------------------------------------------
@router.post("/orders/{order_id}/submit-document", summary="Agent uploads property document")
def submit_document(
    order_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # ✅ Ensure only agents can submit
    require_role(current_user, ["agent"])

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Save uploaded file safely
    filename = f"{current_user.id}_{order_id}_{file.filename}"
    save_path = os.path.join("uploads", "docs", filename)
    with open(save_path, "wb") as f:
        f.write(file.file.read())

    submission = models.DocumentSubmission(
        order_id=order.id,
        agent_id=current_user.id,
        file_url=f"/{save_path}",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "message": "Document submitted successfully.",
        "data": {
            "submission_id": submission.id,
            "file_url": submission.file_url,
        },
    }


@router.patch("/documents/{doc_id}/review", summary="Admin reviews agent document")
def review_document(
    doc_id: int,
    status: str = Form(...),  # expected values: 'approved' | 'rejected'
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    doc = db.query(models.DocumentSubmission).filter(models.DocumentSubmission.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = status
    doc.remarks = remarks
    db.commit()
    db.refresh(doc)

    # ✅ If approved, mark order as completed
    if status == "approved":
        order = db.query(models.Order).filter(models.Order.id == doc.order_id).first()
        if order:
            order.status = "completed"
            db.commit()

    return {
        "message": f"Document {status}.",
        "remarks": remarks,
        "document_id": doc.id,
    }
