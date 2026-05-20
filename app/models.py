# app/models.py

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    func,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base


# =========================
# 👤 USER
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="buyer")
    phone = Column(String(50), nullable=True)
    photo = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # =========================
    # 🔐 ACCOUNT STATUS FLOW
    # =========================
    status = Column(String(30), default="pending")
    # pending | active | rejected | suspended

    is_verified = Column(Integer, default=0)

    verification_notes = Column(Text, nullable=True)

    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    listings = relationship(
        "Listing",
        back_populates="owner",
        foreign_keys="Listing.owner_id"
    )
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete")
    orders = relationship("Order", back_populates="buyer", cascade="all, delete")
    support_tickets = relationship("SupportTicket", back_populates="user", cascade="all, delete")



# =========================
# 🏡 LISTING
# =========================
class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    location = Column(String)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    main_image = Column(String, nullable=True)
    images = Column(JSON, nullable=True, default=list)
    videos = Column(JSON, nullable=True, default=list)
    status = Column(String(50), default="pending")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # =========================
    # 🛡️ MODERATION FLOW
    # =========================
    review_status = Column(String(30), default="pending")
    # pending | approved | rejected | flagged

    flag_reason = Column(Text, nullable=True)

    verified_ownership = Column(Integer, default=0)

    verified_by_admin = Column(Integer, ForeignKey("users.id"), nullable=True)

    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship(
        "User",
        back_populates="listings",
        foreign_keys=[owner_id]
    )

    @property
    def agent(self):
        return self.owner

    favorited_by = relationship("Favorite", back_populates="listing", cascade="all, delete")
    orders = relationship("Order", back_populates="listing", cascade="all, delete")


# =========================
# ESCROW SYSTEM (CORE OF YOUR PLATFORM)
# =========================
class EscrowAccount(Base):
    __tablename__ = "escrow_accounts"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))

    buyer_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("users.id"))

    amount = Column(Float, nullable=False)

    status = Column(String(30), default="held")
    # held | released | refunded | disputed

    payment_reference = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order")


# =========================
# DISPUTE SYSTEM (CRITICAL)
# =========================
class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    raised_by = Column(Integer, ForeignKey("users.id"))

    reason = Column(Text, nullable=False)

    status = Column(String(30), default="open")
    # open | investigating | resolved | rejected

    resolution = Column(String(50), nullable=True)
    # refund_buyer | pay_agent | split | none

    admin_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order")


# =========================
# FRAUD DETECTION SYSTEM
# =========================
class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)

    type = Column(String(50))
    # spam | scam | suspicious | keyword_violation

    severity = Column(String(20), default="low")
    # low | medium | high

    description = Column(Text)

    is_resolved = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resolved_at = Column(DateTime(timezone=True), nullable=True)

    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)


# =========================
# ADMIN AUDIT LOGS (VERY IMPORTANT FOR REAL SYSTEMS)
# =========================
class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    admin_id = Column(Integer, ForeignKey("users.id"))

    action = Column(String(100))
    # approve_user | reject_listing | release_escrow | ban_user

    target_type = Column(String(50))
    # user | listing | order | dispute

    target_id = Column(Integer)

    description = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =========================
# 👀 RECENT VIEWS
# =========================
class RecentView(Base):
    __tablename__ = "recent_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    listing = relationship("Listing")

    # ✅ Prevent duplicates + speed up queries
    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="unique_recent_view"),
        Index("ix_recent_user_listing", "user_id", "listing_id"),
    )


# =========================
# ❤️ FAVORITES
# =========================
class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")
    listing = relationship("Listing", back_populates="favorited_by")

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="unique_user_listing_favorite"),
    )


# =========================
# 🧾 ORDERS
# =========================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"))

    checkout_ref = Column(String(100), index=True, nullable=True)  # ✅ ADD THIS

    status = Column(String(50), default="pending")
    is_cancelled = Column(Integer, default=0)
    payment_status = Column(String(30), default="unpaid")
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    amount = Column(Float, nullable=True)
    admin_confirmed = Column(Integer, default=0)
    agent_document = Column(String(255), nullable=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ORDER MODEL (ESCROW READY)
    escrow_status = Column(String(30), default="not_started")
    # not_started | held | released | refunded | disputed

    dispute_flag = Column(Integer, default=0)

    buyer = relationship("User", back_populates="orders")
    listing = relationship("Listing", back_populates="orders")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    listing_id = Column(Integer, ForeignKey("listings.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ✅ ADD THIS
    listing = relationship("Listing")


# =========================
# 💬 CHAT MESSAGE
# =========================
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Room identifier
    room_id = Column(
        String,
        nullable=False,
        index=True,
    )

    # Sender
    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Receiver
    receiver_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional linked listing
    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Message body
    message = Column(
        Text,
        nullable=False,
    )

    # Timestamp
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # =========================
    # MESSAGE STATES
    # =========================

    # 0 = unread
    # 1 = read
    is_read = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # 0 = not delivered
    # 1 = delivered to recipient device
    delivered = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # 0 = not seen
    # 1 = seen/opened by recipient
    seen = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # =========================
    # RELATIONSHIPS
    # =========================

    sender = relationship(
        "User",
        foreign_keys=[sender_id],
        backref="sent_messages",
    )

    receiver = relationship(
        "User",
        foreign_keys=[receiver_id],
        backref="received_messages",
    )

    listing = relationship(
        "Listing",
        foreign_keys=[listing_id],
    )

    # =========================
    # INDEXES
    # =========================

    __table_args__ = (

        # Fast room history loading
        Index(
            "ix_chat_room_timestamp",
            "room_id",
            "timestamp",
        ),

        # Fast unread message checks
        Index(
            "ix_chat_receiver_read",
            "receiver_id",
            "is_read",
        ),

        # Fast inbox conversation queries
        Index(
            "ix_chat_sender_receiver",
            "sender_id",
            "receiver_id",
        ),

        # Fast realtime sync
        Index(
            "ix_chat_room_receiver",
            "room_id",
            "receiver_id",
        ),
        Index("ix_chat_listing_id", "listing_id"),
    )


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(String, unique=True, index=True, nullable=False)

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )

    buyer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 🔥 NEW
    call_active = Column(Integer, default=0)

    # 🔥 NEW
    last_message = Column(Text, nullable=True)

    # 🔥 NEW
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    # 🔥 NEW
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    listing = relationship("Listing")

    buyer = relationship(
        "User",
        foreign_keys=[buyer_id],
    )

    agent = relationship(
        "User",
        foreign_keys=[agent_id],
    )

    # Prevent duplicate rooms
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "buyer_id",
            "agent_id",
            name="unique_chat_room",
        ),
    )


# =========================
# 📄 DOCUMENT SUBMISSION
# =========================
class DocumentSubmission(Base):
    __tablename__ = "document_submissions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    agent_id = Column(Integer, ForeignKey("users.id"))

    file_url = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order")
    agent = relationship("User")


# =========================
# 🆘 SUPPORT
# =========================
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    message = Column(Text, nullable=False)
    status = Column(String(50), default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="support_tickets")