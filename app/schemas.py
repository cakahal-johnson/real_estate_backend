# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
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
    refresh_token: str  # ✅ Required
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None


# paginated responses
class PaginatedListingsResponse(BaseModel):
    total: int
    items: List[ListingResponse]

    class Config:
        from_attributes = True


# favorites responses
class FavoriteBase(BaseModel):
    listing_id: int


class FavoriteResponse(FavoriteBase):
    id: int
    user_id: int
    created_at: datetime
    listing: Optional["ListingResponse"]

    class Config:
        from_attributes = True


# For nested relationships
from app.schemas import ListingResponse  # forward ref fix
FavoriteResponse.update_forward_refs()


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


# --- Order schemas ---
class OrderBase(BaseModel):
    listing_id: int


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: str


class OrderResponse(BaseModel):
    id: int
    buyer_id: int
    listing_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentRequest(BaseModel):
    order_id: int
    payment_method: str
    amount: float


class PaymentResponse(BaseModel):
    order_id: int
    payment_status: str
    payment_reference: Optional[str]
    amount: float
    timestamp: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    buyer_id: int
    listing_id: int
    status: str
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageBase(BaseModel):
    message: str
    listing_id: Optional[int] = None
    sender_id: int
    receiver_id: int
    timestamp: datetime
    is_read: Optional[int] = 0  # 0 = unread, 1 = read ✅

    class Config:
        from_attributes = True


class FavoriteCheckResponse(BaseModel):
    is_favorited: bool