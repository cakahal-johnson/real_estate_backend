# app/routers/listings.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db
from app.core.security import get_current_active_user, require_agent

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
def create_listing(listing: schemas.ListingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_agent)):
    new_listing = models.Listing(**listing.dict(), owner_id=current_user.id)
    db.add(new_listing)
    db.commit()
    db.refresh(new_listing)
    return new_listing


@router.put("/{listing_id}", response_model=schemas.ListingResponse)
def update_listing(listing_id: int, updated: schemas.ListingUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Only owner (or agent — owner is agent anyway) can update
    if listing.owner_id != current_user.id and current_user.role != "agent":
        raise HTTPException(status_code=403, detail="Not authorized to edit this listing")

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(listing, key, value)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.owner_id != current_user.id and current_user.role != "agent":
        raise HTTPException(status_code=403, detail="Not authorized to delete this listing")

    db.delete(listing)
    db.commit()
    return None


@router.get("/me", response_model=List[schemas.ListingResponse])
def get_my_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_agent)
):
    """
    Return all listings created by the currently logged-in agent.
    Only agents can access this route.
    """
    listings = db.query(models.Listing).filter(models.Listing.owner_id == current_user.id).all()
    return listings