# app/core/email.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from app.core.config import settings
from fastapi import BackgroundTasks
import logging

logger = logging.getLogger(__name__)

# ✅ Email Connection Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,  # plain string, FastAPI-Mail handles securely
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
)

fastmail = FastMail(conf)


# ✅ 1. Account Verification Email
async def send_verification_email(email: EmailStr, token: str):
    """
    Sends an account verification email with a unique tokenized link.
    """
    try:
        verification_link = f"{settings.FRONTEND_URL}/verify?token={token}"
        message = MessageSchema(
            subject="Verify your RealEstateHub Account",
            recipients=[email],
            body=f"""
            <h3>Welcome to RealEstateHub!</h3>
            <p>Click the button below to verify your email:</p>
            <a href="{verification_link}" 
               style="background-color:#007bff;color:#fff;padding:10px 15px;text-decoration:none;border-radius:5px;">
               Verify Email
            </a>
            <p>If you did not create an account, please ignore this message.</p>
            """,
            subtype="html",
        )
        await fastmail.send_message(message)
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")


# ✅ 2. Password Reset Email
async def send_password_reset_email(email: EmailStr, token: str):
    """
    Sends a password reset link to the user’s email.
    """
    try:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        message = MessageSchema(
            subject="Reset your RealEstateHub Password",
            recipients=[email],
            body=f"""
            <h3>Password Reset Request</h3>
            <p>Click the button below to reset your password:</p>
            <a href="{reset_link}" 
               style="background-color:#28a745;color:#fff;padding:10px 15px;text-decoration:none;border-radius:5px;">
               Reset Password
            </a>
            <p>If you didn’t request a reset, ignore this message.</p>
            """,
            subtype="html",
        )
        await fastmail.send_message(message)
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")


# ✅ 3. Generic Notification Email — e.g., Orders, Listings, Admin Alerts
async def send_email_notification(email: EmailStr, subject: str, body: str):
    """
    Sends a generic email notification (HTML-safe).
    """
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=body,
            subtype="html",
        )
        await fastmail.send_message(message)
        logger.info(f"Notification email sent to {email} - {subject}")
    except Exception as e:
        logger.error(f"Failed to send notification email to {email}: {e}")


# ✅ 4. Background Task Wrapper — For Controllers
def queue_email(
    background_tasks: BackgroundTasks,
    email: EmailStr,
    subject: str,
    body: str
):
    """
    Queue an async email to be sent in the background.
    """
    background_tasks.add_task(send_email_notification, email, subject, body)


# ✅ 5. Post-Payment Email to Buyer & Agent
async def send_payment_confirmation_emails(buyer_email: str, agent_email: str, order_id: int, listing_title: str):
    """
    Sends payment confirmation to both buyer and agent.
    """
    try:
        # Buyer confirmation
        buyer_msg = f"""
        <h3>Payment Successful!</h3>
        <p>Your payment for <b>{listing_title}</b> has been received.</p>
        <p>Order ID: <b>{order_id}</b></p>
        <p>Thank you for using RealEstateHub.</p>
        """
        await send_email_notification(buyer_email, "Payment Confirmation", buyer_msg)

        # Agent alert
        agent_msg = f"""
        <h3>New Verified Payment</h3>
        <p>The buyer has completed payment for your listing: <b>{listing_title}</b>.</p>
        <p>Order ID: <b>{order_id}</b></p>
        <p>You may now proceed to upload the required property documents for admin review.</p>
        """
        await send_email_notification(agent_email, "Buyer Payment Confirmed", agent_msg)

        logger.info(f"Payment confirmation emails sent (Order #{order_id})")

    except Exception as e:
        logger.error(f"Error sending payment confirmation emails (Order #{order_id}): {e}")
