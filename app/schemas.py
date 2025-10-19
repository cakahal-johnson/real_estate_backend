# app/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
