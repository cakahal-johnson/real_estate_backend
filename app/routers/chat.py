# app/routers/chat.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime
import json

from app.core.security import decode_access_token
from app.database import get_db
from app import models, schemas
from app.websocket_manager import send_personal_message

router = APIRouter(
    prefix="/chat",
    tags=["Chat (WebSocket + History + Typing + ReadReceipts)"],
)

# --- Manage connected clients ---
active_connections: Dict[str, List[WebSocket]] = {}


# --- Helper: Get user from token ---
def get_current_user_from_token(token: str, db: Session) -> models.User:
    payload = decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# --- HTTP endpoint: Latest conversations ---
@router.get("/conversations")
def get_chat_conversations(
    db: Session = Depends(get_db),
    token: str = Query(...),
):
    user = get_current_user_from_token(token, db)

    # Get latest messages first
    latest_messages = (
        db.query(models.ChatMessage)
        .filter(
            (models.ChatMessage.sender_id == user.id)
            | (models.ChatMessage.receiver_id == user.id)
        )
        .order_by(models.ChatMessage.timestamp.desc())
        .all()
    )

    conversations = {}

    for msg in latest_messages:
        other_user_id = (
            msg.receiver_id
            if msg.sender_id == user.id
            else msg.sender_id
        )

        # Skip duplicates
        if other_user_id in conversations:
            continue

        other_user = (
            db.query(models.User)
            .filter(models.User.id == other_user_id)
            .first()
        )

        conversations[other_user_id] = {
            "id": msg.id,
            "message": msg.message,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "sender_name": (
                other_user.full_name.strip()
                if other_user and other_user.full_name
                else (
                    other_user.email.split("@")[0]
                    if other_user and other_user.email
                    else f"User {other_user_id}"
                )
            ),
            "created_at": msg.timestamp,
            "listing_id": msg.listing_id,
            "other_user_id": other_user_id,
            "room_id": msg.room_id,
            "is_read": msg.is_read,
        }

    return list(conversations.values())


# --- WebSocket Chat Endpoint ---
@router.websocket("/ws/{room_id}")
async def chat_room(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(...),
    receiver_id: int = Query(None),
    listing_id: int = Query(None),
    db: Session = Depends(get_db),
):
    user = get_current_user_from_token(token, db)
    await websocket.accept()

    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)

    try:
        # --- Auto-mark all unread messages as read on connect ---
        unread_msgs = (
            db.query(models.ChatMessage)
            .filter(
                models.ChatMessage.room_id == room_id,
                models.ChatMessage.receiver_id == user.id,
                models.ChatMessage.is_read == 0,
            )
            .all()
        )
        if unread_msgs:
            for msg in unread_msgs:
                msg.is_read = 1
            db.commit()

            # Notify all clients in this room
            for conn in active_connections[room_id]:
                await conn.send_json({
                    "type": "bulk_read",
                    "reader_id": user.id,
                    "room_id": room_id,
                    "count": len(unread_msgs)
                })

        # --- Send chat history ---
        previous_messages = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.room_id == room_id)
            .order_by(models.ChatMessage.timestamp.asc())
            .all()
        )
        history_payload = [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "sender_name": (
                    msg.sender.full_name.strip()
                    if msg.sender and msg.sender.full_name
                    else (
                        msg.sender.email.split("@")[0]
                        if msg.sender and msg.sender.email
                        else f"User {msg.sender_id}"
                    )
                ),
                "message": msg.message,
                "timestamp": str(msg.timestamp),
                "is_read": msg.is_read,
            }
            for msg in previous_messages
        ]

        await websocket.send_json({
            "type": "history",
            "messages": history_payload,
        })

        # --- Handle incoming events ---
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            event_type = data.get("type")

            # --- Typing indicator ---
            if event_type == "typing":
                for conn in active_connections[room_id]:
                    if conn != websocket:
                        await conn.send_json({
                            "type": "typing",
                            "sender_id": user.id,
                            "message": f"{user.full_name or 'User'} is typing...",
                        })

            # --- Send new message ---
            elif event_type == "message":
                content = data.get("message", "")
                if not content.strip():
                    continue

                new_msg = models.ChatMessage(
                    room_id=room_id,
                    sender_id=user.id,
                    receiver_id=receiver_id,
                    listing_id=listing_id,
                    message=content,
                    timestamp=datetime.utcnow(),
                )

                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)

                room = (
                    db.query(models.ChatRoom)
                    .filter(models.ChatRoom.room_id == room_id)
                    .first()
                )

                if room:
                    room.last_message = content
                    room.last_message_at = datetime.utcnow()
                    db.commit()

                payload = {
                    "type": "message",
                    "id": new_msg.id,
                    "sender_id": user.id,
                    "receiver_id": receiver_id,
                    "sender_name": (
                        user.full_name.strip()
                        if user.full_name
                        else user.email.split("@")[0]
                    ),
                    "message": content,
                    "listing_id": listing_id,
                    "timestamp": str(new_msg.timestamp),
                    "is_read": new_msg.is_read,
                }

                # 1. Notify room users
                for conn in active_connections[room_id]:
                    await conn.send_json(payload)

                # 2. 🔥 CRITICAL FIX: notify receiver globally
                await send_personal_message(receiver_id, {
                    "event": "new_message",
                    "data": payload
                })

            # --- Read single message ---
            elif event_type == "read":
                message_id = data.get("message_id")
                if message_id:
                    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
                    if msg and msg.receiver_id == user.id:
                        msg.is_read = 1
                        db.commit()
                        for conn in active_connections[room_id]:
                            await conn.send_json({
                                "type": "read",
                                "message_id": msg.id,
                                "reader_id": user.id,
                            })

    except WebSocketDisconnect:
        active_connections[room_id].remove(websocket)
        if not active_connections[room_id]:
            del active_connections[room_id]


# --- HTTP endpoint: Chat history ---
@router.get("/history/{room_id}", response_model=List[schemas.ChatMessageBase])
def get_chat_history(
    room_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    user = get_current_user_from_token(token, db)
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.room_id == room_id)
        .order_by(models.ChatMessage.timestamp.asc())
        .all()
    )

    # --- Auto-mark unread messages as read when user opens chat ---
    unread_msgs = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.room_id == room_id,
            models.ChatMessage.receiver_id == user.id,
            models.ChatMessage.is_read == 0,
        )
        .all()
    )
    if unread_msgs:
        for msg in unread_msgs:
            msg.is_read = 1
        db.commit()

    return messages


# --- HTTP endpoint: Unread message count per room or sender ---
@router.get("/unread/{user_id}")
def get_unread_messages(
    user_id: int,
    db: Session = Depends(get_db),
    token: str = Query(...),
):
    """
    Return unread message counts for a user.
    Groups results by room_id and sender_id.
    Used to display inbox badges or conversation previews.
    """
    user = get_current_user_from_token(token, db)

    if user.id != user_id:
        raise HTTPException(status_code=403, detail="You are not authorized to view this user's unread messages")

    unread_messages = (
        db.query(
            models.ChatMessage.room_id,
            models.ChatMessage.sender_id,
            func.count(models.ChatMessage.id).label("unread_count")
        )
        .filter(models.ChatMessage.receiver_id == user_id, models.ChatMessage.is_read == 0)
        .group_by(models.ChatMessage.room_id, models.ChatMessage.sender_id)
        .all()
    )

    return [
        {
            "room_id": msg.room_id,
            "sender_id": msg.sender_id,
            "unread_count": msg.unread_count,
        }
        for msg in unread_messages
    ]
