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


# USER VERIFICATION SCHEMAS for ADMIN SECTIONS
class UserStatusUpdate(BaseModel):
    status: str
    # pending | active | rejected | suspended
    notes: Optional[str] = None


class UserVerificationResponse(BaseModel):
    id: int
    status: str
    is_verified: int
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# LISTING MODERATION SCHEMAS
class ListingModerationUpdate(BaseModel):
    review_status: str
    # pending | approved | rejected | flagged

    flag_reason: Optional[str] = None
    verified_ownership: Optional[int] = None


class ListingModerationResponse(BaseModel):
    id: int
    review_status: str
    flag_reason: Optional[str]
    verified_ownership: int
    approved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ESCROW SYSTEM SCHEMAS
class EscrowResponse(BaseModel):
    id: int
    order_id: int
    buyer_id: int
    agent_id: int
    amount: float
    status: str
    payment_reference: Optional[str]
    created_at: datetime
    released_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class EscrowActionRequest(BaseModel):
    action: str
    # hold | release | refund | dispute

    reason: Optional[str] = None


# DISPUTE SYSTEM SCHEMAS
class DisputeCreate(BaseModel):
    order_id: int
    reason: str


class DisputeResponse(BaseModel):
    id: int
    order_id: int
    raised_by: int
    reason: str
    status: str
    resolution: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DisputeResolveRequest(BaseModel):
    resolution: str
    # refund_buyer | pay_agent | split | reject_claim

    admin_notes: Optional[str] = None


# FRAUD DETECTION SCHEMAS
class FraudAlertResponse(BaseModel):
    id: int
    user_id: Optional[int]
    listing_id: Optional[int]
    message_id: Optional[int]
    type: str
    severity: str
    description: str
    is_resolved: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FraudActionRequest(BaseModel):
    action: str
    # warn | suspend | ban | clear

    notes: Optional[str] = None


# ADMIN AUDIT LOG SCHEMAS
class AdminAuditLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: str
    target_id: int
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminActionRequest(BaseModel):
    action: str
    target_type: str
    target_id: int
    description: Optional[str] = None


# ENHANCED CHAT SCHEMA (for admin monitoring)
class ChatAdminView(BaseModel):
    id: int
    room_id: str
    sender_id: int
    receiver_id: int
    message: str
    timestamp: datetime
    is_read: int
    delivered: int
    seen: int
    listing_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class EscrowActionResponse(BaseModel):
    escrow_id: int
    status: str
    message: str
    released_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DisputeActionResponse(BaseModel):
    dispute_id: int
    status: str
    resolution: Optional[str]
    message: str
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FraudScoreResponse(BaseModel):
    user_id: Optional[int]
    score: int
    level: str
    # low | medium | high | critical

    reasons: List[str]

    model_config = ConfigDict(from_attributes=True)


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int

    total_listings: int
    pending_listings: int
    flagged_listings: int

    total_orders: int
    completed_orders: int
    disputed_orders: int

    total_revenue: float

    fraud_alerts: int

    open_tickets: int

    model_config = ConfigDict(from_attributes=True)