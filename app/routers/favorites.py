# app/routers/favorites.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Union
from app import models, schemas
from app.database import get_db
from app.core.security import get_current_active_user
from sqlalchemy import func

router = APIRouter(prefix="/favorites", tags=["Favorites"], include_in_schema=True)


@router.post("/{listing_id}", response_model=schemas.FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.listing_id == listing_id
    ).first()

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
    return db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id
    ).all()


@router.get("/dashboard", response_model=List[Dict[str, Union[str, int]]])
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

    return [{"category": category, "count": count} for category, count in result]


@router.get("/check/{listing_id}", response_model=schemas.FavoriteCheckResponse)
def check_if_favorited(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    exists = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.listing_id == listing_id
    ).first()

    return {"is_favorited": bool(exists)}


@router.post("/toggle/{listing_id}", response_model=schemas.FavoriteCheckResponse)
def toggle_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.listing_id == listing_id
    ).first()

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
    fav = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.listing_id == listing_id
    ).first()

    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(fav)
    db.commit()
