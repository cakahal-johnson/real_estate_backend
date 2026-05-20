# app/services/moderation_service.py

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models


# =========================================================
# MODERATION SERVICE
# =========================================================

class ModerationService:

    # =====================================================
    # VERIFY USER
    # =====================================================
    @staticmethod
    def verify_user(
        db: Session,
        user_id: int,
        admin_id: int,
        notes: Optional[str] = None,
    ) -> models.User:

        user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        user.status = "active"
        user.is_verified = 1
        user.verification_notes = notes
        user.verified_by = admin_id
        user.verified_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return user

    # =====================================================
    # REJECT USER
    # =====================================================
    @staticmethod
    def reject_user(
        db: Session,
        user_id: int,
        admin_id: int,
        notes: Optional[str] = None,
    ) -> models.User:

        user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        user.status = "rejected"
        user.is_verified = 0
        user.verification_notes = notes
        user.verified_by = admin_id
        user.verified_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return user

    # =====================================================
    # SUSPEND USER
    # =====================================================
    @staticmethod
    def suspend_user(
        db: Session,
        user_id: int,
        admin_id: int,
        notes: Optional[str] = None,
    ) -> models.User:

        user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        user.status = "suspended"
        user.verification_notes = notes
        user.verified_by = admin_id

        db.commit()
        db.refresh(user)

        return user

    # =====================================================
    # APPROVE LISTING
    # =====================================================
    @staticmethod
    def approve_listing(
        db: Session,
        listing_id: int,
        admin_id: int,
    ) -> models.Listing:

        listing = (
            db.query(models.Listing)
            .filter(models.Listing.id == listing_id)
            .first()
        )

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Listing not found",
            )

        # ---------------------------------------------
        # Validate agent verification
        # ---------------------------------------------
        if listing.owner and listing.owner.is_verified != 1:
            raise HTTPException(
                status_code=400,
                detail="Agent account is not verified",
            )

        listing.status = "approved"

        listing.review_status = "approved"
        listing.flag_reason = None
        listing.verified_ownership = 1
        listing.verified_by_admin = admin_id
        listing.approved_at = datetime.utcnow()

        db.commit()
        db.refresh(listing)

        return listing

    # =====================================================
    # REJECT LISTING
    # =====================================================
    @staticmethod
    def reject_listing(
        db: Session,
        listing_id: int,
        admin_id: int,
        reason: Optional[str] = None,
    ) -> models.Listing:

        listing = (
            db.query(models.Listing)
            .filter(models.Listing.id == listing_id)
            .first()
        )

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Listing not found",
            )

        listing.status = "rejected"

        listing.review_status = "rejected"
        listing.flag_reason = reason
        listing.verified_by_admin = admin_id

        db.commit()
        db.refresh(listing)

        return listing

    # =====================================================
    # FLAG LISTING
    # =====================================================
    @staticmethod
    def flag_listing(
        db: Session,
        listing_id: int,
        admin_id: int,
        reason: str,
    ) -> models.Listing:

        listing = (
            db.query(models.Listing)
            .filter(models.Listing.id == listing_id)
            .first()
        )

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Listing not found",
            )

        listing.review_status = "flagged"
        listing.flag_reason = reason
        listing.verified_by_admin = admin_id

        db.commit()
        db.refresh(listing)

        return listing

    # =====================================================
    # RESET LISTING REVIEW
    # =====================================================
    @staticmethod
    def reset_listing_review(
        db: Session,
        listing_id: int,
    ) -> models.Listing:

        listing = (
            db.query(models.Listing)
            .filter(models.Listing.id == listing_id)
            .first()
        )

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Listing not found",
            )

        listing.review_status = "pending"
        listing.flag_reason = None
        listing.verified_ownership = 0
        listing.verified_by_admin = None
        listing.approved_at = None

        db.commit()
        db.refresh(listing)

        return listing

    # =====================================================
    # GET PENDING USERS
    # =====================================================
    @staticmethod
    def get_pending_users(
        db: Session,
    ):

        return (
            db.query(models.User)
            .filter(models.User.status == "pending")
            .order_by(models.User.created_at.desc())
            .all()
        )

    # =====================================================
    # GET PENDING LISTINGS
    # =====================================================
    @staticmethod
    def get_pending_listings(
        db: Session,
    ):

        return (
            db.query(models.Listing)
            .filter(models.Listing.review_status == "pending")
            .order_by(models.Listing.created_at.desc())
            .all()
        )

    # =====================================================
    # GET FLAGGED LISTINGS
    # =====================================================
    @staticmethod
    def get_flagged_listings(
        db: Session,
    ):

        return (
            db.query(models.Listing)
            .filter(models.Listing.review_status == "flagged")
            .order_by(models.Listing.updated_at.desc())
            .all()
        )