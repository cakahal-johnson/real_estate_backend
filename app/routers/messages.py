# app/routers/messages.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.core.security import get_current_user
from app.websocket_manager import send_personal_message
import asyncio
from sqlalchemy import or_, and_, desc

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/", response_model=schemas.MessageOut)
def create_message(
    message: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Send a message to another user (agent or customer)."""
    receiver = db.query(models.User).filter(models.User.id == message.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    db_message = models.Message(
        sender_id=current_user.id,
        receiver_id=message.receiver_id,
        listing_id=message.listing_id,
        content=message.content,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # ✅ Send WebSocket notification to receiver (real-time update)
    try:
        asyncio.create_task(
            send_personal_message(
                db_message.receiver_id,
                {
                    "event": "new_message",
                    "data": {
                        "id": db_message.id,
                        "content": db_message.content,
                        "sender_id": db_message.sender_id,
                        "listing_id": db_message.listing_id,
                        "created_at": str(db_message.created_at),
                    },
                },
            )
        )
    except Exception as e:
        print("⚠️ WebSocket notify failed:", e)

    return db_message


@router.get("/inbox", response_model=list[schemas.MessageOut])
def get_inbox(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve all messages received by the current user."""
    return (
        db.query(models.Message)
        .filter(models.Message.receiver_id == current_user.id)
        .order_by(models.Message.created_at.desc())
        .all()
    )


@router.get("/sent", response_model=list[schemas.MessageOut])
def get_sent_messages(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve all messages sent by the current user."""
    return (
        db.query(models.Message)
        .filter(models.Message.sender_id == current_user.id)
        .order_by(models.Message.created_at.desc())
        .all()
    )


@router.get("/conversations")
def get_conversations(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
):
    """
    Returns latest conversation per user.
    """

    messages = (
        db.query(models.Message)
        .filter(
            or_(
                models.Message.sender_id == current_user.id,
                models.Message.receiver_id == current_user.id,
            )
        )
        .order_by(desc(models.Message.created_at))
        .all()
    )

    conversations = {}

    for msg in messages:
        other_user_id = (
            msg.receiver_id
            if msg.sender_id == current_user.id
            else msg.sender_id
        )

        # Keep latest message only
        if other_user_id in conversations:
            continue

        other_user = (
            db.query(models.User)
            .filter(models.User.id == other_user_id)
            .first()
        )

        conversations[other_user_id] = {
            "id": msg.id,
            "message": msg.content,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "sender_name": (
                other_user.full_name
                if other_user
                else "User"
            ),
            "created_at": msg.created_at,
            "listing_id": msg.listing_id,
            "other_user_id": other_user_id,
        }

    return list(conversations.values())