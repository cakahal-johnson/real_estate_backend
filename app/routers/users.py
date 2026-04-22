# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app import schemas, models
from app.database import get_db
from app.core.security import get_password_hash, get_current_active_user


import shutil
import os
from uuid import uuid4


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role or "buyer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_active_user)):
    return current_user


@router.patch("/update-profile", response_model=schemas.UserResponse)
def update_profile(
    update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    # RE-ATTACH USER TO CURRENT SESSION
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.email and update.email != user.email:
        if db.query(models.User).filter(models.User.email == update.email).first():
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = update.email

    if update.full_name is not None:
        user.full_name = update.full_name.strip()

    if update.password:
        user.password_hash = get_password_hash(update.password)

    if update.phone is not None:
        user.phone = update.phone

    if update.photo is not None:
        user.photo = update.photo

    db.commit()
    db.refresh(user)

    return user


# added for phone upload
@router.post("/upload-photo", response_model=schemas.UserResponse)
def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image format")

    # file size check
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    # delete old
    if user.photo:
        old_path = os.path.join(os.getcwd(), user.photo.lstrip("/"))
        if os.path.exists(old_path):
            os.remove(old_path)

    # create filename
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid4()}{ext}"

    upload_dir = os.path.join(os.getcwd(), "uploads", "users")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # save DB path
    user.photo = f"/uploads/users/{filename}"

    db.commit()
    db.refresh(user)

    return user
