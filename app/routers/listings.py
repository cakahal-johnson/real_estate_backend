# app/routers/listings.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("/", response_model=List[schemas.ListingResponse])
def get_listings(db: Session = Depends(get_db)):
    listings = db.query(models.Listing).all()
    return listings


@router.get("/{listing_id}", response_model=schemas.ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/", response_model=schemas.ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(listing: schemas.ListingCreate, db: Session = Depends(get_db)):
    new_listing = models.Listing(**listing.dict())
    db.add(new_listing)
    db.commit()
    db.refresh(new_listing)
    return new_listing


@router.put("/{listing_id}", response_model=schemas.ListingResponse)
def update_listing(listing_id: int, updated: schemas.ListingUpdate, db: Session = Depends(get_db)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(listing, key, value)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.delete(listing)
    db.commit()
    return None
