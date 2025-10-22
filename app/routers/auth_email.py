from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.email import send_verification_email, send_password_reset_email
from jose import jwt, JWTError
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Auth Email"])


# --- Register with email verification ---
@router.post("/register", response_model=schemas.UserResponse)
async def register_user(user_in: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        is_active=False,  # require verification
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email}, expires_delta=timedelta(hours=24))
    background_tasks.add_task(send_verification_email, user.email, token)

    return user


# --- Verify Email ---
@router.get("/verify")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        email = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = True
        db.commit()
        return {"message": "Email verified successfully"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")


# --- Password Reset Request ---
@router.post("/forgot-password")
async def forgot_password(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_access_token({"sub": user.email}, expires_delta=timedelta(hours=1))
    background_tasks.add_task(send_password_reset_email, user.email, token)
    return {"message": "Password reset email sent"}


# --- Password Reset ---
@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        email = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.password_hash = get_password_hash(new_password)
        db.commit()
        return {"message": "Password reset successful"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
