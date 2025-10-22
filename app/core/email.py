# app/core/email.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from app.core.config import settings

# ✅ Use plain string for MAIL_PASSWORD — FastAPI-Mail will handle it safely
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,  # <-- no SecretStr()
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
)

fastmail = FastMail(conf)


# ✅ 1. Verification Email
async def send_verification_email(email: EmailStr, token: str):
    verification_link = f"http://localhost:8000/auth/verify?token={token}"
    message = MessageSchema(
        subject="Verify your RealEstateHub Account",
        recipients=[email],
        body=f"""
        <h3>Welcome to RealEstateHub!</h3>
        <p>Click below to verify your email:</p>
        <a href="{verification_link}">Verify Email</a>
        """,
        subtype="html",
    )
    await fastmail.send_message(message)


# ✅ 2. Password Reset Email
async def send_password_reset_email(email: EmailStr, token: str):
    reset_link = f"http://localhost:8000/auth/reset-password?token={token}"
    message = MessageSchema(
        subject="Reset your RealEstateHub Password",
        recipients=[email],
        body=f"""
        <h3>Password Reset Request</h3>
        <p>Click below to reset your password:</p>
        <a href="{reset_link}">Reset Password</a>
        """,
        subtype="html",
    )
    await fastmail.send_message(message)


# ✅ 3. Generic Notification Email — for Orders, Listings, etc.
async def send_email_notification(email: EmailStr, subject: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html",
    )
    await fastmail.send_message(message)
