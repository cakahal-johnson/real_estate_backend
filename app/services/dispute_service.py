# app/services/dispute_service.py

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


# =========================================================
# DISPUTE SERVICE
# =========================================================

class DisputeService:

    # =====================================================
    # RAISE DISPUTE
    # =====================================================
    @staticmethod
    def raise_dispute(
        db: Session,
        order_id: int,
        raised_by: int,
        reason: str,
    ) -> models.Dispute:

        order = (
            db.query(models.Order)
            .filter(models.Order.id == order_id)
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # ---------------------------------------------
        # Prevent duplicate dispute
        # ---------------------------------------------
        existing = (
            db.query(models.Dispute)
            .filter(models.Dispute.order_id == order_id)
            .first()
        )

        if existing:
            return existing

        dispute = models.Dispute(
            order_id=order_id,
            raised_by=raised_by,
            reason=reason,
            status="open",
        )

        # ---------------------------------------------
        # Update order
        # ---------------------------------------------
        order.status = "disputed"
        order.dispute_flag = 1
        order.escrow_status = "disputed"

        db.add(dispute)
        db.commit()
        db.refresh(dispute)

        return dispute

    # =====================================================
    # UPDATE DISPUTE STATUS (ADMIN FLOW)
    # =====================================================
    @staticmethod
    def update_dispute_status(
        db: Session,
        dispute_id: int,
        status: str,
        admin_notes: Optional[str] = None,
    ) -> models.Dispute:

        dispute = (
            db.query(models.Dispute)
            .filter(models.Dispute.id == dispute_id)
            .first()
        )

        if not dispute:
            raise HTTPException(
                status_code=404,
                detail="Dispute not found",
            )

        dispute.status = status
        dispute.admin_notes = admin_notes

        # ---------------------------------------------
        # If resolved, set timestamp
        # ---------------------------------------------
        if status == "resolved":
            dispute.resolved_at = datetime.utcnow()

        db.commit()
        db.refresh(dispute)

        return dispute

    # =====================================================
    # RESOLUTION ENGINE (CORE LOGIC)
    # =====================================================
    @staticmethod
    def resolve_dispute(
        db: Session,
        dispute_id: int,
        resolution: str,
        admin_notes: Optional[str] = None,
    ) -> models.Dispute:

        dispute = (
            db.query(models.Dispute)
            .filter(models.Dispute.id == dispute_id)
            .first()
        )

        if not dispute:
            raise HTTPException(
                status_code=404,
                detail="Dispute not found",
            )

        order = dispute.order

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Related order not found",
            )

        # ---------------------------------------------
        # Apply resolution decision
        # ---------------------------------------------
        valid_resolutions = ["refund_buyer", "pay_agent", "split", "reject_claim"]

        if resolution not in valid_resolutions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resolution. Must be one of {valid_resolutions}",
            )

        dispute.resolution = resolution
        dispute.status = "resolved"
        dispute.admin_notes = admin_notes
        dispute.resolved_at = datetime.utcnow()

        # ---------------------------------------------
        # Update ORDER + ESCROW LOGIC
        # ---------------------------------------------
        escrow = (
            db.query(models.EscrowAccount)
            .filter(models.EscrowAccount.order_id == order.id)
            .first()
        )

        if resolution == "refund_buyer":
            order.status = "cancelled"
            order.escrow_status = "refunded"

            if escrow:
                escrow.status = "refunded"

        elif resolution == "pay_agent":
            order.status = "completed"
            order.escrow_status = "released"
            order.completed_at = datetime.utcnow()

            if escrow:
                escrow.status = "released"
                escrow.released_at = datetime.utcnow()

        elif resolution == "split":
            order.status = "completed"
            order.escrow_status = "released"

            if escrow:
                escrow.status = "released"
                escrow.released_at = datetime.utcnow()

        elif resolution == "reject_claim":
            order.status = "completed"
            order.escrow_status = "released"

        db.commit()
        db.refresh(dispute)

        return dispute

    # =====================================================
    # GET DISPUTE BY ORDER
    # =====================================================
    @staticmethod
    def get_dispute_by_order(
        db: Session,
        order_id: int,
    ) -> Optional[models.Dispute]:

        return (
            db.query(models.Dispute)
            .filter(models.Dispute.order_id == order_id)
            .first()
        )

    # =====================================================
    # GET ALL DISPUTES
    # =====================================================
    @staticmethod
    def get_all_disputes(
        db: Session,
    ):

        return (
            db.query(models.Dispute)
            .order_by(models.Dispute.created_at.desc())
            .all()
        )

    # =====================================================
    # GET OPEN DISPUTES
    # =====================================================
    @staticmethod
    def get_open_disputes(
        db: Session,
    ):

        return (
            db.query(models.Dispute)
            .filter(models.Dispute.status == "open")
            .order_by(models.Dispute.created_at.desc())
            .all()
        )