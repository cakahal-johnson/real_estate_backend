from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db
from app.core.security import get_current_active_user
from sqlalchemy import func

router = APIRouter(prefix="/favorites", tags=["Favorites"])


@router.post("/{listing_id}", response_model=schemas.FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Add a listing to user's favorites"""
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(models.Favorite).filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already favorited")

    fav = models.Favorite(user_id=current_user.id, listing_id=listing_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


@router.get("/", response_model=List[schemas.FavoriteResponse])
def get_my_favorites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Return all listings favorited by the current user"""
    favorites = db.query(models.Favorite).filter(models.Favorite.user_id == current_user.id).all()
    return favorites


@router.get("/dashboard")
def favorites_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    result = (
        db.query(models.Listing.category, func.count(models.Favorite.id))
        .join(models.Favorite, models.Favorite.listing_id == models.Listing.id)
        .filter(models.Favorite.user_id == current_user.id)
        .group_by(models.Listing.category)
        .all()
    )
    return [{"category": cat, "count": cnt} for cat, cnt in result]


@router.get("/check/{listing_id}")
def check_if_favorited(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    ✅ Check if the given listing is already favorited by the current user.
    Returns: {"is_favorited": true/false}
    """
    exists = (
        db.query(models.Favorite)
        .filter_by(user_id=current_user.id, listing_id=listing_id)
        .first()
        is not None
    )
    return {"is_favorited": exists}


@router.post("/toggle/{listing_id}")
def toggle_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    ✅ Toggle favorite state for a given listing.
    - If already favorited → remove it.
    - If not → add it.
    Returns: {"is_favorited": true/false}
    """
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(models.Favorite).filter_by(user_id=current_user.id, listing_id=listing_id).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"is_favorited": False}

    fav = models.Favorite(user_id=current_user.id, listing_id=listing_id)
    db.add(fav)
    db.commit()
    return {"is_favorited": True}


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Remove a favorite listing"""
    fav = db.query(models.Favorite).filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(fav)
    db.commit()
    return None
