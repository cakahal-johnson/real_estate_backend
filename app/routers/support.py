# app/routers/support.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.core.security import get_current_active_user
from fastapi import HTTPException

router = APIRouter(prefix="/support", tags=["Support"])


@router.post("/ticket", response_model=schemas.SupportTicketResponse)
def create_ticket(
    ticket: schemas.SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    new_ticket = models.SupportTicket(
        user_id=current_user.id,
        message=ticket.message
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


@router.get("/tickets", response_model=list[schemas.SupportTicketResponse])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return (
        db.query(models.SupportTicket)
        .filter(models.SupportTicket.user_id == current_user.id)
        .order_by(models.SupportTicket.created_at.desc())
        .all()
    )


# Admin
@router.patch("/ticket/{id}")
def update_ticket_status(
    id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),  # ✅ add this
):
    # ADMIN CHECK HERE
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    ticket = (
        db.query(models.SupportTicket)
        .filter(models.SupportTicket.id == id)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = status
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/admin/tickets")
def get_all_tickets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    return db.query(models.SupportTicket).order_by(
        models.SupportTicket.created_at.desc()
    ).all()