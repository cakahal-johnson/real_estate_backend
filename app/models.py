# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    price = Column(Float, nullable=False)
    location = Column(String(100))
    image_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
