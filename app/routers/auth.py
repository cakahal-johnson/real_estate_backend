# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app import models, schemas
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from jose import jwt, JWTError

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token_data = {"user_id": user.id, "email": user.email, "role": user.role}

    # ✅ Create access + refresh tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # ✅ Now defined
        "token_type": "bearer"
    }


@router.post("/refresh")
def refresh_token(request: Request):
    auth_header = request.headers.get("authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.REFRESH_TOKEN_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Optional safety check (HIGHLY RECOMMENDED)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        new_access = create_access_token({
            "user_id": payload["user_id"],
            "email": payload["email"],
            "role": payload["role"],
        })

        return {
            "access_token": new_access,
            "refresh_token": token
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")