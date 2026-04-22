# app/routers/recent_views.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import RecentView, Listing
from app.core.security import get_current_active_user

router = APIRouter(prefix="/recent-views", tags=["Recent Views"])


# ---------------- CREATE / ADD VIEW ----------------
@router.post("/")
def add_recent_view(
    listing_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    # ✅ Validate listing exists FIRST
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ Prevent duplicates (move to top behavior)
    existing = db.query(RecentView).filter(
        RecentView.user_id == current_user.id,
        RecentView.listing_id == listing_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()  # commit delete before re-adding

    # ✅ Add new view
    view = RecentView(
        user_id=current_user.id,
        listing_id=listing_id
    )

    db.add(view)
    db.commit()

    # ✅ Keep only latest 10 records (auto cleanup)
    views = (
        db.query(RecentView)
        .filter(RecentView.user_id == current_user.id)
        .order_by(desc(RecentView.created_at))
        .all()
    )

    for v in views[10:]:
        db.delete(v)

    db.commit()

    return {"message": "recent view saved"}


# ---------------- GET RECENT VIEWS ----------------
@router.get("/")
def get_recent_views(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    views = (
        db.query(RecentView)
        .filter(RecentView.user_id == current_user.id)
        .order_by(desc(RecentView.created_at))
        .limit(10)
        .all()
    )

    # ✅ Preserve order
    listing_ids = [v.listing_id for v in views]

    listings = db.query(Listing).filter(Listing.id.in_(listing_ids)).all()

    listing_map = {l.id: l for l in listings}

    ordered_listings = [
        listing_map[lid] for lid in listing_ids if lid in listing_map
    ]

    return ordered_listings


# ---------------- DELETE ALL RECENT ----------------
@router.delete("/")
def clear_recent_views(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    db.query(RecentView).filter(
        RecentView.user_id == current_user.id
    ).delete()

    db.commit()

    return {"message": "cleared"}