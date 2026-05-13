# app/routers/chat.py

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Query,
    HTTPException,
    Header,
)

from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.core.security import decode_access_token
from app.database import get_db
from app import models

from app.websocket_manager import (
    connect_room,
    disconnect_room,
    send_room_message,
    send_personal_message,
    mark_message_seen,
    mark_message_delivered,
    online_users,
)

router = APIRouter(
    prefix="/chat",
    tags=["Chat (WebSocket + History + Typing + ReadReceipts)"],
)


# =====================================
# AUTH HELPER
# =====================================
def get_current_user_from_token(token: str, db: Session) -> models.User:
    payload = decode_access_token(token)

    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = (
        db.query(models.User)
        .filter(models.User.id == payload["user_id"])
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# =====================================
# NORMALIZE MESSAGE
# =====================================
def normalize_message(msg: models.ChatMessage):
    return {
        "id": msg.id,
        "room_id": msg.room_id,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,

        "sender_name": (
            msg.sender.full_name.strip()
            if msg.sender and msg.sender.full_name
            else (
                msg.sender.email.split("@")[0]
                if msg.sender
                else "User"
            )
        ),

        "message": msg.message,
        "listing_id": msg.listing_id,

        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,

        "is_read": bool(msg.is_read),
        "delivered": bool(msg.delivered),
        "seen": bool(msg.seen),
    }


# =====================================
# CONVERSATIONS LIST
# =====================================
@router.get("/conversations")
def get_conversations(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    user = get_current_user_from_token(token, db)

    subquery = (
        db.query(
            models.ChatMessage.room_id,
            func.max(models.ChatMessage.timestamp).label("latest")
        )
        .filter(
            (models.ChatMessage.sender_id == user.id)
            | (models.ChatMessage.receiver_id == user.id)
        )
        .group_by(models.ChatMessage.room_id)
        .subquery()
    )

    latest_messages = (
        db.query(models.ChatMessage)
        .join(
            subquery,
            (models.ChatMessage.room_id == subquery.c.room_id)
            & (models.ChatMessage.timestamp == subquery.c.latest)
        )
        .order_by(models.ChatMessage.timestamp.desc())
        .all()
    )

    conversations = []
    seen_rooms = set()

    for msg in latest_messages:
        if msg.room_id in seen_rooms:
            continue

        seen_rooms.add(msg.room_id)

        other_user_id = (
            msg.receiver_id if msg.sender_id == user.id else msg.sender_id
        )

        other_user = (
            db.query(models.User)
            .filter(models.User.id == other_user_id)
            .first()
        )

        conversations.append({
            "id": msg.id,
            "room_id": msg.room_id,
            "message": msg.message,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "other_user_name": (
                other_user.full_name.strip()
                if other_user and other_user.full_name
                else (
                    other_user.email.split("@")[0]
                    if other_user
                    else "User"
                )
            ),
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "listing_id": msg.listing_id,
            "other_user_id": other_user_id,
            "is_read": bool(msg.is_read),
            "delivered": bool(msg.delivered),
            "seen": bool(msg.seen),
        })

    return conversations


# =====================================
# WEBSOCKET CHAT
# =====================================
@router.websocket("/ws/{room_id}")
async def chat_room(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(...),
    receiver_id: int = Query(...),
    listing_id: int = Query(None),
    db: Session = Depends(get_db),
):

    # AUTH
    user = get_current_user_from_token(token, db)

    # CONNECT
    await websocket.accept()
    await connect_room(room_id, websocket)

    try:
        # MARK UNREAD AS READ
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
                msg.is_read = True
                msg.seen = True

            db.commit()

            await send_room_message(room_id, {
                "type": "bulk_read",
                "reader_id": user.id,
                "room_id": room_id,
                "count": len(unread_msgs),
            })

        # HISTORY
        previous_messages = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.room_id == room_id)
            .order_by(models.ChatMessage.timestamp.asc())
            .all()
        )

        await websocket.send_json({
            "type": "history",
            "messages": [normalize_message(m) for m in previous_messages],
        })

        # LOOP
        while True:
            raw_data = await websocket.receive_text()

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type")

            # TYPING
            if event_type == "typing":
                await send_room_message(
                    room_id,
                    {"type": "typing", "sender_id": user.id},
                    exclude=websocket,
                )

            # STOP TYPING
            elif event_type == "stop_typing":
                await send_room_message(
                    room_id,
                    {"type": "stop_typing", "sender_id": user.id},
                    exclude=websocket,
                )

            # MESSAGE
            elif event_type == "message":
                content = data.get("message", "").strip()
                if not content:
                    continue

                new_msg = models.ChatMessage(
                    room_id=room_id,
                    sender_id=user.id,
                    receiver_id=receiver_id,
                    listing_id=listing_id,
                    message=content,
                    timestamp=datetime.utcnow(),
                    is_read=False,
                    delivered=False,
                    seen=False,
                )

                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)

                payload = {
                    "type": "message",
                    **normalize_message(new_msg),
                }

                await send_room_message(room_id, payload)

                await send_personal_message(receiver_id, {
                    "event": "new_message",
                    "data": payload,
                })

                # DELIVERED
                if receiver_id in online_users or receiver_id == user.id:
                    await mark_message_delivered(new_msg.id)

                    new_msg.delivered = True  # FIX consistency

                    await send_room_message(room_id, {
                        "type": "delivered",
                        "message_id": new_msg.id,
                    })

            # READ RECEIPT
            elif event_type == "read":
                message_id = data.get("message_id")
                if not message_id:
                    continue

                msg = (
                    db.query(models.ChatMessage)
                    .filter(models.ChatMessage.id == message_id)
                    .first()
                )

                if not msg or msg.receiver_id != user.id:
                    continue

                msg.is_read = True
                msg.seen = True

                db.commit()

                await mark_message_seen(msg.id)

                await send_room_message(room_id, {
                    "type": "read",
                    "message_id": msg.id,
                    "reader_id": user.id,
                })

    except WebSocketDisconnect:
        await disconnect_room(room_id, websocket)

    except Exception as e:
        print(f"❌ Chat error: {e}")
        await disconnect_room(room_id, websocket)


# =====================================
# HISTORY HTTP
# =====================================
@router.get("/history/{room_id}")
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

    for msg in messages:
        if msg.receiver_id == user.id and not msg.is_read:
            msg.is_read = True
            msg.seen = True

    db.commit()

    return [normalize_message(m) for m in messages]


# =====================================
# UNREAD COUNTS
# =====================================
@router.get("/unread/{user_id}")
def get_unread_messages(
    user_id: int,
    db: Session = Depends(get_db),
    token: str = Query(...),
):
    user = get_current_user_from_token(token, db)

    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    unread_messages = (
        db.query(
            models.ChatMessage.room_id,
            models.ChatMessage.sender_id,
            func.count(models.ChatMessage.id).label("unread_count"),
        )
        .filter(
            models.ChatMessage.receiver_id == user_id,
            models.ChatMessage.is_read == 0,
        )
        .group_by(
            models.ChatMessage.room_id,
            models.ChatMessage.sender_id,
        )
        .all()
    )

    return [
        {
            "room_id": m.room_id,
            "sender_id": m.sender_id,
            "unread_count": m.unread_count,
        }
        for m in unread_messages
    ]