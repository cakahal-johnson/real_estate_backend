# app/schemas.py
from pydantic import BaseModel, EmailStr,  Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
import re


class UserBase(BaseModel):
    id: int
    full_name: Optional[str]
    email: EmailStr
    phone: Optional[str] = None
    photo: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Listing schemas ---
class ListingBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    location: Optional[str] = None

    lat: Optional[float] = None
    lng: Optional[float] = None

    main_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    videos: List[str] = Field(default_factory=list)


class ListingCreate(ListingBase):
    pass


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    location: Optional[str] = None

    lat: Optional[float] = None
    lng: Optional[float] = None

    main_image: Optional[str] = None
    images: Optional[List[str]] = None
    videos: Optional[List[str]] = None


class ListingResponse(ListingBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    agent: Optional[UserBase] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_agent(cls, listing):
        data = cls.model_validate(listing)
        data.agent = listing.owner
        return data


# --- User schemas ---
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    role: Optional[str] = "buyer"

    # ✅ Full name validation
    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()

        if len(v) < 3:
            raise ValueError("Full name must be at least 3 characters")

        if not re.match(r"^[A-Za-z\s.'-]+$", v):
            raise ValueError("Full name contains invalid characters")

        return v

    # ✅ Phone validation
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        v = v.strip().replace(" ", "")

        # Accept:
        # +2348012345678
        # 08012345678

        if not re.match(r"^(\+234|0)[789][01]\d{8}$", v):
            raise ValueError("Invalid phone number format")

        return v

    # ✅ Password validation
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        v = v.strip()

        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")

        return v


class UserResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: EmailStr
    role: str
    phone: Optional[str] = None  # ADD
    photo: Optional[str] = None  # ADD
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# favorites responses
class FavoriteBase(BaseModel):
    listing_id: int


class FavoriteResponse(FavoriteBase):
    id: int
    user_id: int
    created_at: datetime
    listing: Optional["ListingResponse"]

    model_config = ConfigDict(from_attributes=True)


# For nested relationships
FavoriteResponse.model_rebuild()


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None  # ADD
    photo: Optional[str] = None  # ADD


# --- Order schemas ---
class OrderBase(BaseModel):
    listing_id: int


# app/schemas.py
class OrderCreate(BaseModel):
    listing_id: int

    model_config = ConfigDict(extra="ignore")  # 👈 ignore extra fields instead of failing


class CartCreate(BaseModel):
    listing_id: int


class OrderCancelResponse(BaseModel):
    message: str
    order_id: int


class OrderUpdate(BaseModel):
    status: str


class OrderResponse(BaseModel):
    id: int
    buyer_id: int
    listing_id: int
    status: str
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount: Optional[float] = None
    admin_confirmed: Optional[int] = 0
    agent_document: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    listing: Optional[ListingResponse] = None  # ✅ REQUIRED

    model_config = ConfigDict(from_attributes=True)


class PaginatedOrdersResponse(BaseModel):
    orders: List[OrderResponse]
    hasMore: bool
    total: int  # ✅ ADD THIS


class PaymentRequest(BaseModel):
    checkout_ref: str
    order_ids: List[int] = Field(default_factory=list)
    amount: float
    payment_method: str = "paystack"


class PaymentResponse(BaseModel):
    order_id: int
    payment_status: str
    payment_reference: Optional[str]
    amount: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageBase(BaseModel):
    message: str
    listing_id: Optional[int] = None
    sender_id: int
    receiver_id: int
    timestamp: Optional[datetime] = None
    is_read: Optional[int] = 0  # 0 = unread, 1 = read ✅

    model_config = ConfigDict(from_attributes=True)


class FavoriteCheckResponse(BaseModel):
    is_favorited: bool


# --- Message schemas ---
class MessageBase(BaseModel):
    receiver_id: int
    listing_id: Optional[int] = None
    content: str


class MessageCreate(MessageBase):
    pass


class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    listing_id: Optional[int] = None
    content: str

    delivered: Optional[int] = 0
    seen: Optional[int] = 0

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# support pages
class SupportTicketCreate(BaseModel):
    message: str


class SupportTicketResponse(BaseModel):
    id: int
    message: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaystackVerifyRequest(BaseModel):
    reference: str
    order_id: int
