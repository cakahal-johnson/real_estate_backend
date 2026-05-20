# app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app import models

from app.core.security import get_current_user, require_admin, require_role

# SERVICES
from app.services.admin_dashboard_service import AdminDashboardService
from app.services.audit_service import AuditService
from app.services.moderation_service import ModerationService
from app.services.fraud_service import FraudService
from app.services.dispute_service import DisputeService
from app.services.escrow_service import EscrowService

router = APIRouter(prefix="/admin", tags=["Admin"])

os.makedirs("uploads/docs", exist_ok=True)


# =========================================================
# 📊 ADMIN DASHBOARD (NEW CONNECTED SERVICE)
# =========================================================
@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return AdminDashboardService.get_dashboard_summary(db)


# =========================================================
# 👤 USERS MANAGEMENT
# =========================================================
@router.get("/users")
def list_users(db: Session = Depends(get_db),
               current_user: models.User = Depends(require_admin)):

    return db.query(models.User).all()


@router.delete("/users/{user_id}")
def delete_user(user_id: int,
                 db: Session = Depends(get_db),
                 current_user: models.User = Depends(require_admin)):

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    db.delete(user)
    db.commit()

    AuditService.log_action(
        db=db,
        admin_id=current_user.id,
        action="delete_user",
        target_type="user",
        target_id=user_id,
    )

    return {"message": "User deleted"}


# =========================================================
# 🏘 LISTINGS (CONNECTED TO MODERATION SERVICE)
# =========================================================
@router.patch("/listings/{listing_id}/approve")
def approve_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    listing = ModerationService.approve_listing(
        db=db,
        listing_id=listing_id,
        admin_id=current_user.id,
    )

    AuditService.log_listing_action(
        db=db,
        admin_id=current_user.id,
        listing_id=listing_id,
        action="approve_listing",
    )

    return {"message": "Listing approved", "id": listing.id}


@router.patch("/listings/{listing_id}/reject")
def reject_listing(
    listing_id: int,
    reason: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    listing = ModerationService.reject_listing(
        db=db,
        listing_id=listing_id,
        admin_id=current_user.id,
        reason=reason,
    )

    AuditService.log_listing_action(
        db=db,
        admin_id=current_user.id,
        listing_id=listing_id,
        action="reject_listing",
        reason=reason,
    )

    return {"message": "Listing rejected", "id": listing.id}


# =========================================================
# 🧾 ORDERS
# =========================================================
@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    order.status = status
    db.commit()

    AuditService.log_action(
        db=db,
        admin_id=current_user.id,
        action="update_order_status",
        target_type="order",
        target_id=order_id,
        description=status,
    )

    return {"message": "Order updated"}


# =========================================================
# 💰 ESCROW ACTIONS (CONNECTED SERVICE)
# =========================================================
@router.post("/escrow/{escrow_id}/release")
def release_escrow(
    escrow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    escrow = EscrowService.release_funds(db, escrow_id)

    AuditService.log_escrow_action(
        db=db,
        admin_id=current_user.id,
        order_id=escrow.order_id,
        action="release_escrow",
    )

    return {"message": "Escrow released"}


@router.post("/escrow/{escrow_id}/refund")
def refund_escrow(
    escrow_id: int,
    reason: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    escrow = EscrowService.refund_buyer(db, escrow_id, reason)

    AuditService.log_escrow_action(
        db=db,
        admin_id=current_user.id,
        order_id=escrow.order_id,
        action="refund_escrow",
        description=reason,
    )

    return {"message": "Refund processed"}


# ========================================================
# Update User Role
# ========================================================
@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    # optional validation (important)
    allowed_roles = ["admin", "agent", "buyer"]
    if role not in allowed_roles:
        raise HTTPException(400, "Invalid role")

    user.role = role
    db.commit()

    AuditService.log_action(
        db=db,
        admin_id=current_user.id,
        action="update_user_role",
        target_type="user",
        target_id=user_id,
        description=role,
    )

    return {"message": "User role updated", "id": user.id, "role": user.role}

# =========================================================
# 🚨 FRAUD (CONNECTED SERVICE)
# =========================================================
@router.get("/fraud/alerts")
def get_fraud_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    return FraudService.get_active_alerts(db)


@router.post("/fraud/resolve/{alert_id}")
def resolve_fraud_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    alert = FraudService.resolve_alert(
        db=db,
        alert_id=alert_id,
        admin_id=current_user.id,
    )

    return {"message": "Fraud alert resolved"}


# =========================================================
# ⚖️ DISPUTES (CONNECTED SERVICE)
# =========================================================
@router.get("/disputes")
def get_disputes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    return DisputeService.get_all_disputes(db)


@router.post("/disputes/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: int,
    resolution: str,
    admin_notes: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    dispute = DisputeService.resolve_dispute(
        db=db,
        dispute_id=dispute_id,
        resolution=resolution,
        admin_notes=admin_notes,
    )

    AuditService.log_dispute_action(
        db=db,
        admin_id=current_user.id,
        dispute_id=dispute_id,
        action="resolve_dispute",
        notes=admin_notes,
    )

    return {"message": "Dispute resolved"}


# =========================================================
# 💬 CHATS
# =========================================================
@router.get("/chats")
def list_chats(db: Session = Depends(get_db),
               current_user: models.User = Depends(require_admin)):

    return db.query(models.ChatMessage).all()


# =========================================================
# 📄 DOCUMENT REVIEW (IMPROVED)
# =========================================================
@router.patch("/documents/{doc_id}/review")
def review_document(
    doc_id: int,
    status: str = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):

    doc = db.query(models.DocumentSubmission).filter(
        models.DocumentSubmission.id == doc_id
    ).first()

    if not doc:
        raise HTTPException(404, "Document not found")

    doc.status = status
    doc.remarks = remarks

    db.commit()

    # auto complete order
    if status == "approved":
        order = db.query(models.Order).filter(models.Order.id == doc.order_id).first()
        if order:
            order.status = "completed"
            db.commit()

    AuditService.log_action(
        db=db,
        admin_id=current_user.id,
        action="review_document",
        target_type="document",
        target_id=doc_id,
        description=status,
    )

    return {"message": "Document reviewed"}