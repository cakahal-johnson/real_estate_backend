# app/services/fraud_service.py

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app import models


# =========================================================
# FRAUD SERVICE
# =========================================================

class FraudService:

    # =====================================================
    # BLOCKED / SUSPICIOUS KEYWORDS
    # =====================================================
    SUSPICIOUS_KEYWORDS = [
        "send money outside platform",
        "bitcoin",
        "crypto",
        "western union",
        "pay directly",
        "bank transfer only",
        "urgent payment",
        "fake document",
        "refund me first",
        "otp",
        "pin",
        "password",
        "wire transfer",
        "investment scheme",
        "click this link",
        "whatsapp only",
    ]

    HIGH_RISK_WORDS = [
        "password",
        "otp",
        "bank login",
        "send pin",
        "crypto",
        "bitcoin",
    ]

    # =====================================================
    # DETECT MESSAGE FRAUD
    # =====================================================
    @staticmethod
    def analyze_chat_message(
        db: Session,
        message: models.ChatMessage,
    ) -> Optional[models.FraudAlert]:

        if not message:
            return None

        text = (message.message or "").lower()

        matched_keywords = []

        for keyword in FraudService.SUSPICIOUS_KEYWORDS:
            if keyword in text:
                matched_keywords.append(keyword)

        # ---------------------------------------------
        # No fraud detected
        # ---------------------------------------------
        if not matched_keywords:
            return None

        # ---------------------------------------------
        # Determine severity
        # ---------------------------------------------
        severity = "low"

        for risk_word in FraudService.HIGH_RISK_WORDS:
            if risk_word in text:
                severity = "high"
                break

        if len(matched_keywords) >= 3:
            severity = "medium"

        # ---------------------------------------------
        # Prevent duplicate alert
        # ---------------------------------------------
        existing = (
            db.query(models.FraudAlert)
            .filter(models.FraudAlert.message_id == message.id)
            .first()
        )

        if existing:
            return existing

        # ---------------------------------------------
        # Create fraud alert
        # ---------------------------------------------
        fraud_alert = models.FraudAlert(
            user_id=message.sender_id,
            listing_id=message.listing_id,
            message_id=message.id,
            type="keyword_violation",
            severity=severity,
            description=f"Suspicious keywords detected: {', '.join(matched_keywords)}",
        )

        db.add(fraud_alert)
        db.commit()
        db.refresh(fraud_alert)

        return fraud_alert

    # =====================================================
    # ANALYZE LISTING
    # =====================================================
    @staticmethod
    def analyze_listing(
        db: Session,
        listing: models.Listing,
    ) -> Optional[models.FraudAlert]:

        if not listing:
            return None

        text = f"{listing.title} {listing.description}".lower()

        suspicious_terms = [
            "cheap deal",
            "urgent sale",
            "no inspection",
            "direct payment",
            "outside platform",
            "crypto only",
            "instant transfer",
        ]

        matched = []

        for term in suspicious_terms:
            if term in text:
                matched.append(term)

        if not matched:
            return None

        # ---------------------------------------------
        # Create alert
        # ---------------------------------------------
        fraud_alert = models.FraudAlert(
            user_id=listing.owner_id,
            listing_id=listing.id,
            type="suspicious_listing",
            severity="medium",
            description=f"Listing contains suspicious phrases: {', '.join(matched)}",
        )

        db.add(fraud_alert)

        # ---------------------------------------------
        # Flag listing automatically
        # ---------------------------------------------
        listing.review_status = "flagged"
        listing.flag_reason = "Automatic fraud detection triggered"

        db.commit()
        db.refresh(fraud_alert)

        return fraud_alert

    # =====================================================
    # USER RISK SCORE
    # =====================================================
    @staticmethod
    def calculate_user_risk_score(
        db: Session,
        user_id: int,
    ) -> dict:

        alerts = (
            db.query(models.FraudAlert)
            .filter(models.FraudAlert.user_id == user_id)
            .all()
        )

        total_alerts = len(alerts)

        high = len([a for a in alerts if a.severity == "high"])
        medium = len([a for a in alerts if a.severity == "medium"])
        low = len([a for a in alerts if a.severity == "low"])

        score = (
            (high * 50)
            + (medium * 20)
            + (low * 10)
        )

        risk_level = "low"

        if score >= 100:
            risk_level = "high"
        elif score >= 40:
            risk_level = "medium"

        return {
            "user_id": user_id,
            "total_alerts": total_alerts,
            "risk_score": score,
            "risk_level": risk_level,
            "high_alerts": high,
            "medium_alerts": medium,
            "low_alerts": low,
        }

    # =====================================================
    # RESOLVE ALERT
    # =====================================================
    @staticmethod
    def resolve_alert(
        db: Session,
        alert_id: int,
        admin_id: int,
    ) -> models.FraudAlert:

        alert = (
            db.query(models.FraudAlert)
            .filter(models.FraudAlert.id == alert_id)
            .first()
        )

        if not alert:
            raise Exception("Fraud alert not found")

        alert.is_resolved = 1
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = admin_id

        db.commit()
        db.refresh(alert)

        return alert

    # =====================================================
    # AUTO SUSPEND HIGH RISK USERS
    # =====================================================
    @staticmethod
    def auto_suspend_high_risk_user(
        db: Session,
        user_id: int,
    ) -> bool:

        risk_data = FraudService.calculate_user_risk_score(
            db=db,
            user_id=user_id,
        )

        if risk_data["risk_level"] != "high":
            return False

        user = (
            db.query(models.User)
            .filter(models.User.id == user_id)
            .first()
        )

        if not user:
            return False

        user.status = "suspended"

        db.commit()

        return True

    # =====================================================
    # GET ACTIVE ALERTS
    # =====================================================
    @staticmethod
    def get_active_alerts(
        db: Session,
    ) -> List[models.FraudAlert]:

        return (
            db.query(models.FraudAlert)
            .filter(models.FraudAlert.is_resolved == 0)
            .order_by(models.FraudAlert.created_at.desc())
            .all()
        )

    # =====================================================
    # GET HIGH RISK ALERTS
    # =====================================================
    @staticmethod
    def get_high_risk_alerts(
        db: Session,
    ) -> List[models.FraudAlert]:

        return (
            db.query(models.FraudAlert)
            .filter(
                models.FraudAlert.severity == "high",
                models.FraudAlert.is_resolved == 0,
            )
            .order_by(models.FraudAlert.created_at.desc())
            .all()
        )