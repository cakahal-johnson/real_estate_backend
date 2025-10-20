# app/routers/listings.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.database import get_db
from app.core.security import get_current_active_user, require_agent

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("/", response_model=schemas.PaginatedListingsResponse)
def get_listings(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by title or description"),
    location: Optional[str] = Query(None, description="Filter by location"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of listings to return"),
    sort_by: str = Query("created_at", description="Sort by: price or created_at"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
):
    """
    Get listings with optional filters, search, sorting, and pagination.
    Returns { total, items } for frontend pagination support.
    """
    query = db.query(models.Listing)

    # --- Filtering and Search ---
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (models.Listing.title.ilike(search_term)) |
            (models.Listing.description.ilike(search_term))
        )

    if location:
        query = query.filter(models.Listing.location.ilike(f"%{location.lower()}%"))

    if min_price is not None:
        query = query.filter(models.Listing.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Listing.price <= max_price)

    # --- Total count (before pagination) ---
    total = query.count()

    # --- Sorting ---
    sort_column = models.Listing.created_at
    if sort_by == "price":
        sort_column = models.Listing.price
    elif sort_by == "title":
        sort_column = models.Listing.title

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # --- Pagination ---
    listings = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": listings
    }


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