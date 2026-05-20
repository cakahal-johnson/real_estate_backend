# app/services/audit_service.py

from sqlalchemy.orm import Session
from typing import Optional

from app import models


class AuditService:

    @staticmethod
    def log_action(
        db: Session,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int,
        description: Optional[str] = None,
    ):
        audit = models.AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description,
        )

        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    # ---------------------------
    @staticmethod
    def log_user_verification(db, admin_id, user_id, status, notes=None):
        return AuditService.log_action(
            db, admin_id, f"user_{status}", "user", user_id, notes
        )

    # ---------------------------
    @staticmethod
    def log_listing_action(db, admin_id, listing_id, action, reason=None):
        return AuditService.log_action(
            db, admin_id, action, "listing", listing_id, reason
        )

    # ---------------------------
    @staticmethod
    def log_escrow_action(db, admin_id, order_id, action, description=None):
        return AuditService.log_action(
            db, admin_id, action, "order", order_id, description
        )

    # ---------------------------
    @staticmethod
    def log_dispute_action(db, admin_id, dispute_id, action, notes=None):
        return AuditService.log_action(
            db, admin_id, action, "dispute", dispute_id, notes
        )

    # ---------------------------
    @staticmethod
    def get_all_logs(db: Session, limit: int = 100):
        return (
            db.query(models.AdminAuditLog)
            .order_by(models.AdminAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )