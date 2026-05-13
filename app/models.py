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

    # Relationships
    listings = relationship("Listing", back_populates="owner")
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

    # Relationships
    owner = relationship("User", back_populates="listings")

    @property
    def agent(self):
        return self.owner

    favorited_by = relationship("Favorite", back_populates="listing", cascade="all, delete")
    orders = relationship("Order", back_populates="listing", cascade="all, delete")


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