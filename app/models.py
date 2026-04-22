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
    main_image = Column(String, nullable=True)
    images = Column(JSON, nullable=True, default=[])
    status = Column(String(50), default="pending")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="listings")
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

    status = Column(String(50), default="pending")
    is_cancelled = Column(Integer, default=0) # comment out
    payment_status = Column(String(30), default="unpaid")
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    amount = Column(Float, nullable=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    admin_confirmed = Column(Integer, default=0)
    agent_document = Column(String(255), nullable=True)

    buyer = relationship("User", back_populates="orders")
    listing = relationship("Listing", back_populates="orders")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    listing_id = Column(Integer, ForeignKey("listings.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =========================
# 💬 CHAT MESSAGE
# =========================
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, nullable=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)

    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Integer, default=0)

    sender = relationship("User", foreign_keys=[sender_id])
    listing = relationship("Listing", foreign_keys=[listing_id])


# =========================
# 📩 DIRECT MESSAGE
# =========================
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    listing_id = Column(Integer, ForeignKey("listings.id"))

    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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