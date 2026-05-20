# app/services/escrow_service.py

from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

from app import models


# =========================================================
# ESCROW SERVICE
# =========================================================

class EscrowService:

    # =====================================================
    # HOLD FUNDS
    # =====================================================
    @staticmethod
    def hold_funds(
        db: Session,
        order: models.Order,
    ) -> models.EscrowAccount:

        # ---------------------------------------------
        # Validate Order
        # ---------------------------------------------
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        # ---------------------------------------------
        # Prevent duplicate escrow
        # ---------------------------------------------
        existing = (
            db.query(models.EscrowAccount)
            .filter(models.EscrowAccount.order_id == order.id)
            .first()
        )

        if existing:
            return existing

        # ---------------------------------------------
        # Validate listing owner
        # ---------------------------------------------
        if not order.listing:
            raise HTTPException(
                status_code=400,
                detail="Listing not attached to order",
            )

        # ---------------------------------------------
        # Create escrow account
        # ---------------------------------------------
        escrow = models.EscrowAccount(
            order_id=order.id,
            buyer_id=order.buyer_id,
            agent_id=order.listing.owner_id,
            amount=order.amount or order.listing.price,
            status="held",
            payment_reference=order.payment_reference,
        )

        db.add(escrow)

        # ---------------------------------------------
        # Update order
        # ---------------------------------------------
        order.escrow_status = "held"
        order.status = "in_escrow"

        db.commit()
        db.refresh(escrow)

        return escrow

    # =====================================================
    # RELEASE FUNDS TO AGENT
    # =====================================================
    @staticmethod
    def release_funds(
        db: Session,
        escrow_id: int,
    ) -> models.EscrowAccount:

        escrow = (
            db.query(models.EscrowAccount)
            .filter(models.EscrowAccount.id == escrow_id)
            .first()
        )

        if not escrow:
            raise HTTPException(
                status_code=404,
                detail="Escrow account not found",
            )

        # ---------------------------------------------
        # Prevent invalid release
        # ---------------------------------------------
        if escrow.status == "released":
            raise HTTPException(
                status_code=400,
                detail="Funds already released",
            )

        if escrow.status == "refunded":
            raise HTTPException(
                status_code=400,
                detail="Escrow already refunded",
            )

        # ---------------------------------------------
        # Release escrow
        # ---------------------------------------------
        escrow.status = "released"
        escrow.released_at = datetime.utcnow()

        # ---------------------------------------------
        # Update order
        # ---------------------------------------------
        order = escrow.order

        if order:
            order.escrow_status = "released"
            order.status = "completed"
            order.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(escrow)

        return escrow

    # =====================================================
    # REFUND BUYER
    # =====================================================
    @staticmethod
    def refund_buyer(
            db: Session,
            escrow_id: int,
            reason: Optional[str] = None,
    ) -> models.EscrowAccount:

        escrow = (
            db.query(models.EscrowAccount)
            .filter(models.EscrowAccount.id == escrow_id)
            .first()
        )

        if not escrow:
            raise HTTPException(
                status_code=404,
                detail="Escrow account not found",
            )

        # ---------------------------------------------
        # Prevent invalid refund
        # ---------------------------------------------
        if escrow.status == "released":
            raise HTTPException(
                status_code=400,
                detail="Funds already released to agent",
            )

        if escrow.status == "refunded":
            raise HTTPException(
                status_code=400,
                detail="Escrow already refunded",
            )

        # ---------------------------------------------
        # Refund escrow
        # ---------------------------------------------
        escrow.status = "refunded"

        # ---------------------------------------------
        # Update order
        # ---------------------------------------------
        order = escrow.order

        if order:
            order.escrow_status = "refunded"
            order.status = "cancelled"
            order.is_cancelled = 1

        db.commit()
        db.refresh(escrow)

        return escrow

    # =====================================================
    # MARK AS DISPUTED
    # =====================================================
    @staticmethod
    def mark_as_disputed(
        db: Session,
        escrow_id: int,
    ) -> models.EscrowAccount:

        escrow = (
            db.query(models.EscrowAccount)
            .filter(models.EscrowAccount.id == escrow_id)
            .first()
        )

        if not escrow:
            raise HTTPException(
                status_code=404,
                detail="Escrow account not found",
            )

        # ---------------------------------------------
        # Update escrow
        # ---------------------------------------------
        escrow.status = "disputed"

        # ---------------------------------------------
        # Update order
        # ---------------------------------------------
        order = escrow.order

        if order:
            order.escrow_status = "disputed"
            order.dispute_flag = 1
            order.status = "disputed"

        db.commit()
        db.refresh(escrow)

        return escrow

    # =====================================================
    # GET ESCROW BY ORDER
    # =====================================================
    @staticmethod
    def get_order_escrow(
        db: Session,
        order_id: int,
    ) -> models.EscrowAccount:

        escrow = (
            db.query(models.EscrowAccount)
            .filter(models.EscrowAccount.order_id == order_id)
            .first()
        )

        if not escrow:
            raise HTTPException(
                status_code=404,
                detail="Escrow not found for this order",
            )

        return escrow

    # =====================================================
    # GET ALL ESCROW ACCOUNTS
    # =====================================================
    @staticmethod
    def list_all_escrows(
        db: Session,
    ):

        return (
            db.query(models.EscrowAccount)
            .order_by(models.EscrowAccount.created_at.desc())
            .all()
        )