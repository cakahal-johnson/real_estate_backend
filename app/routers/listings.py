# app/routers/listings.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from app import models, schemas
from app.database import get_db
from app.core.security import get_current_active_user, require_agent


router = APIRouter(prefix="/listings", tags=["Listings"])


# =========================
# 🔍 GET LISTINGS
# =========================
@router.get("/", response_model=schemas.PaginatedListingsResponse)
def get_listings(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    query = db.query(models.Listing)

    # 🔎 Search
    if search:
        term = f"%{search}%"
        query = query.filter(
            models.Listing.title.ilike(term) |
            models.Listing.description.ilike(term)
        )

    # 📍 Location filter
    if location:
        query = query.filter(models.Listing.location.ilike(f"%{location}%"))

    # 💰 Price filters
    if min_price is not None:
        query = query.filter(models.Listing.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Listing.price <= max_price)

    total = query.count()

    # 📊 Sorting
    sort_column = {
        "price": models.Listing.price,
        "title": models.Listing.title,
    }.get(sort_by, models.Listing.created_at)

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    items = query.offset(skip).limit(limit).all()

    return {"total": total, "items": items}


# =========================
# 👤 MY LISTINGS
# =========================
@router.get("/me", response_model=List[schemas.ListingResponse])
def get_my_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_agent),
):
    return db.query(models.Listing).filter(
        models.Listing.owner_id == current_user.id
    ).all()


# =========================
# 🔥 TRENDING LOCATIONS
# =========================
@router.get("/trending-locations")
def get_trending_locations(db: Session = Depends(get_db)):
    results = (
        db.query(
            models.Listing.location,
            func.count(models.Listing.id).label("count")
        )
        .filter(models.Listing.location.isnot(None))
        .filter(models.Listing.location != "")
        .group_by(models.Listing.location)
        .order_by(func.count(models.Listing.id).desc())
        .limit(10)
        .all()
    )

    return [
        {"location": location, "count": count}
        for location, count in results
    ]


# =========================
# 🔥 MOST VIEWED THIS WEEK
# =========================
@router.get("/most-viewed-week")
def get_most_viewed_week(db: Session = Depends(get_db)):
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    results = (
        db.query(
            models.Listing,
            func.count(models.RecentView.id).label("views")
        )
        .join(models.RecentView, models.RecentView.listing_id == models.Listing.id)
        .filter(models.RecentView.created_at >= one_week_ago)
        .group_by(models.Listing.id, models.Listing.location)
        .order_by(func.count(models.RecentView.id).desc())
        .limit(10)
        .all()
    )

    return [
        {
            "id": listing.id,
            "title": listing.title,
            "location": listing.location,
            "price": listing.price,
            "main_image": listing.main_image,
            "views": views,
        }
        for listing, views in results
    ]


# =========================
# 📄 GET SINGLE LISTING (LAST)
# =========================
@router.get("/{listing_id}", response_model=schemas.ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(models.Listing).filter(
        models.Listing.id == listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        **listing.__dict__,
        "agent": listing.owner
    }


# =========================
# ➕ CREATE LISTING
# =========================
@router.post("/", response_model=schemas.ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    listing: schemas.ListingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_agent),
):
    data = listing.dict(exclude={"images", "videos", "main_image"})

    clean_images = [img for img in listing.images if img and img.strip()]

    new_listing = models.Listing(
        **data,
        images=clean_images,
        main_image=clean_images[0] if clean_images else None,
        owner_id=current_user.id,
    )

    db.add(new_listing)
    db.commit()
    db.refresh(new_listing)
    return new_listing


# =========================
# ✏️ UPDATE LISTING
# =========================
@router.put("/{listing_id}", response_model=schemas.ListingResponse)
def update_listing(
    listing_id: int,
    updated: schemas.ListingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    listing = db.query(models.Listing).filter(
        models.Listing.id == listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.owner_id != current_user.id and current_user.role != "agent":
        raise HTTPException(status_code=403, detail="Not authorized")

    data = updated.dict(exclude_unset=True, exclude_none=True)
    data.pop("videos", None)

    if "images" in data:
        clean_images = [img for img in data["images"] if img and img.strip()]
        data["images"] = clean_images
        data["main_image"] = clean_images[0] if clean_images else None

    for k, v in data.items():
        setattr(listing, k, v)

    db.commit()
    db.refresh(listing)
    return listing


# =========================
# 🗑 DELETE LISTING
# =========================
@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    listing = db.query(models.Listing).filter(
        models.Listing.id == listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.owner_id != current_user.id and current_user.role != "agent":
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(listing)
    db.commit()
    return None