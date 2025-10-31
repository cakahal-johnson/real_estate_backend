# app/models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.dialects.sqlite import JSON  # for SQLite, or use postgresql.JSON for Postgres


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="buyer")  # 'agent' or 'buyer'
    phone = Column(String(50), nullable=True)  # new
    photo = Column(String(255), nullable=True)  # optional agent avatar
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ✅ Define relationship to listings
    listings = relationship("Listing", back_populates="owner")
    # ✅ Define relationship to Favorites
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete")
    # Orders
    orders = relationship("Order", back_populates="buyer", cascade="all, delete")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    location = Column(String)
    main_image = Column(String, nullable=True)  # New
    images = Column(JSON, nullable=True, default=[])  # Array of extra images
    owner_id = Column(Integer, ForeignKey("users.id"))  # foreign key link
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ Relationship back to user
    owner = relationship("User", back_populates="listings")
    # add to favorite
    favorited_by = relationship("Favorite", back_populates="listing", cascade="all, delete")
    # Orders
    orders = relationship("Order", back_populates="listing", cascade="all, delete")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")
    listing = relationship("Listing", back_populates="favorited_by")

    # ✅ Prevent duplicates
    __table_args__ = (UniqueConstraint('user_id', 'listing_id', name='unique_user_listing_favorite'),)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"))
    status = Column(String(50), default="pending")  # pending / approved / paid / completed / cancelled
    payment_status = Column(String(30), default="unpaid")  # unpaid / paid / failed
    payment_method = Column(String(50), nullable=True)  # e.g. card, transfer, wallet
    payment_reference = Column(String(100), nullable=True)
    amount = Column(Float, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    buyer = relationship("User", back_populates="orders")
    listing = relationship("Listing", back_populates="orders")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, nullable=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Integer, default=0)  # 0 = unread, 1 = read ✅

    sender = relationship("User", foreign_keys=[sender_id])
    listing = relationship("Listing", foreign_keys=[listing_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    listing_id = Column(Integer, ForeignKey("listings.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


