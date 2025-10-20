# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="buyer")  # 'agent' or 'buyer'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ✅ Define relationship to listings
    listings = relationship("Listing", back_populates="owner")
    # ✅ Define relationship to Favorites
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    location = Column(String)
    image_url = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))  # ✅ foreign key link
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ Relationship back to user
    owner = relationship("User", back_populates="listings")
    favorited_by = relationship("Favorite", back_populates="listing", cascade="all, delete")


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
