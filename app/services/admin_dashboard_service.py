# app/services/admin_dashboard_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func


from app import models


# =========================================================
# ADMIN DASHBOARD SERVICE
# =========================================================

class AdminDashboardService:

    # =====================================================
    # MAIN DASHBOARD STATS
    # =====================================================
    @staticmethod
    def get_dashboard_summary(db: Session) -> dict:

        total_users = db.query(func.count(models.User.id)).scalar() or 0
        active_users = (
            db.query(func.count(models.User.id))
            .filter(models.User.status == "active")
            .scalar()
            or 0
        )

        total_listings = db.query(func.count(models.Listing.id)).scalar() or 0

        pending_listings = (
            db.query(func.count(models.Listing.id))
            .filter(models.Listing.review_status == "pending")
            .scalar()
            or 0
        )

        flagged_listings = (
            db.query(func.count(models.Listing.id))
            .filter(models.Listing.review_status == "flagged")
            .scalar()
            or 0
        )

        total_orders = db.query(func.count(models.Order.id)).scalar() or 0

        completed_orders = (
            db.query(func.count(models.Order.id))
            .filter(models.Order.status == "completed")
            .scalar()
            or 0
        )

        disputed_orders = (
            db.query(func.count(models.Order.id))
            .filter(models.Order.status == "disputed")
            .scalar()
            or 0
        )

        total_revenue = db.query(func.sum(models.Order.amount)).scalar() or 0.0

        fraud_alerts = (
            db.query(func.count(models.FraudAlert.id))
            .filter(models.FraudAlert.is_resolved == 0)
            .scalar()
            or 0
        )

        open_tickets = (
            db.query(func.count(models.SupportTicket.id))
            .filter(models.SupportTicket.status == "open")
            .scalar()
            or 0
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_listings": total_listings,
            "pending_listings": pending_listings,
            "flagged_listings": flagged_listings,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "disputed_orders": disputed_orders,
            "total_revenue": float(total_revenue),
            "fraud_alerts": fraud_alerts,
            "open_tickets": open_tickets,
        }

    # =====================================================
    # USER GROWTH TREND (LAST 7 DAYS)
    # =====================================================
    @staticmethod
    def get_user_growth(db: Session):

        return (
            db.query(
                func.date(models.User.created_at).label("date"),
                func.count(models.User.id).label("count"),
            )
            .group_by(func.date(models.User.created_at))
            .order_by(func.date(models.User.created_at))
            .all()
        )

    # =====================================================
    # REVENUE TREND (LAST 7 DAYS)
    # =====================================================
    @staticmethod
    def get_revenue_trend(db: Session):

        return (
            db.query(
                func.date(models.Order.created_at).label("date"),
                func.sum(models.Order.amount).label("revenue"),
            )
            .filter(models.Order.status == "completed")
            .group_by(func.date(models.Order.created_at))
            .order_by(func.date(models.Order.created_at))
            .all()
        )

    # =====================================================
    # LISTING STATUS BREAKDOWN
    # =====================================================
    @staticmethod
    def get_listing_breakdown(db: Session):

        return {
            "approved": db.query(func.count(models.Listing.id))
            .filter(models.Listing.review_status == "approved")
            .scalar() or 0,

            "pending": db.query(func.count(models.Listing.id))
            .filter(models.Listing.review_status == "pending")
            .scalar() or 0,

            "rejected": db.query(func.count(models.Listing.id))
            .filter(models.Listing.review_status == "rejected")
            .scalar() or 0,

            "flagged": db.query(func.count(models.Listing.id))
            .filter(models.Listing.review_status == "flagged")
            .scalar() or 0,
        }

    # =====================================================
    # FRAUD RISK OVERVIEW
    # =====================================================
    @staticmethod
    def get_fraud_overview(db: Session):

        high = (
            db.query(func.count(models.FraudAlert.id))
            .filter(models.FraudAlert.severity == "high")
            .scalar()
            or 0
        )

        medium = (
            db.query(func.count(models.FraudAlert.id))
            .filter(models.FraudAlert.severity == "medium")
            .scalar()
            or 0
        )

        low = (
            db.query(func.count(models.FraudAlert.id))
            .filter(models.FraudAlert.severity == "low")
            .scalar()
            or 0
        )

        return {
            "high": high,
            "medium": medium,
            "low": low,
        }

    # =====================================================
    # ESCROW SUMMARY (SYSTEM SAFETY METRIC)
    # =====================================================
    @staticmethod
    def get_escrow_summary(db: Session):

        held = (
            db.query(func.count(models.EscrowAccount.id))
            .filter(models.EscrowAccount.status == "held")
            .scalar()
            or 0
        )

        released = (
            db.query(func.count(models.EscrowAccount.id))
            .filter(models.EscrowAccount.status == "released")
            .scalar()
            or 0
        )

        refunded = (
            db.query(func.count(models.EscrowAccount.id))
            .filter(models.EscrowAccount.status == "refunded")
            .scalar()
            or 0
        )

        disputed = (
            db.query(func.count(models.EscrowAccount.id))
            .filter(models.EscrowAccount.status == "disputed")
            .scalar()
            or 0
        )

        return {
            "held": held,
            "released": released,
            "refunded": refunded,
            "disputed": disputed,
        }