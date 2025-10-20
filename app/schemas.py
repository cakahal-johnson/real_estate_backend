# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# --- Listing schemas ---
class ListingBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    location: Optional[str] = None
    image_url: Optional[str] = None


class ListingCreate(ListingBase):
    pass


class ListingUpdate(ListingBase):
    pass


class ListingResponse(ListingBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        # allow ORM objects (SQLAlchemy)
        # orm_mode = True
        from_attributes = True


# --- User schemas ---
class UserCreate(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    password: str
    role: Optional[str] = "buyer"


class UserResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        orm_mode = True


# --- Auth / Token schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
