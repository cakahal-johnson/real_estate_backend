# app/websocket_manager.py

from fastapi import WebSocket
from typing import Dict, List, Set, Optional
from app.database import SessionLocal
from app import models

# =========================================
# CONNECTION STORAGE
# =========================================
user_connections: Dict[int, List[WebSocket]] = {}
room_connections: Dict[str, List[WebSocket]] = {}
online_users: Set[int] = set()


# =========================================
# CONNECT USER
# =========================================
async def connect_user(user_id: int, websocket: WebSocket):
    await websocket.accept()

    if user_id not in user_connections:
        user_connections[user_id] = []

    if websocket not in user_connections[user_id]:
        user_connections[user_id].append(websocket)

    online_users.add(user_id)

    await broadcast_online_users()


# =========================================
# DISCONNECT USER
# =========================================
async def disconnect_user(user_id: int, websocket: WebSocket):
    connections = user_connections.get(user_id, [])

    if websocket in connections:
        connections.remove(websocket)

    if not connections:
        user_connections.pop(user_id, None)
        online_users.discard(user_id)

    await broadcast_online_users()


# =========================================
# CONNECT ROOM
# =========================================
async def connect_room(room_id: str, websocket: WebSocket):
    if room_id not in room_connections:
        room_connections[room_id] = []

    if websocket not in room_connections[room_id]:
        room_connections[room_id].append(websocket)


# =========================================
# DISCONNECT ROOM
# =========================================
async def disconnect_room(room_id: str, websocket: WebSocket):
    connections = room_connections.get(room_id, [])

    if websocket in connections:
        connections.remove(websocket)

    if not connections:
        room_connections.pop(room_id, None)


# =========================================
# SEND TO USER
# =========================================
async def send_personal_message(user_id: int, message: dict):
    connections = user_connections.get(user_id, [])

    dead = []

    for conn in list(connections):
        try:
            await conn.send_json(message)
        except:
            dead.append(conn)

    for d in dead:
        if d in connections:
            connections.remove(d)

    if not connections:
        user_connections.pop(user_id, None)
        online_users.discard(user_id)


# =========================================
# SEND TO ROOM
# =========================================
async def send_room_message(
    room_id: str,
    message: dict,
    exclude: Optional[WebSocket] = None,
):
    connections = room_connections.get(room_id, [])

    dead = []

    for conn in list(connections):

        if exclude and conn == exclude:
            continue

        try:
            await conn.send_json(message)
        except:
            dead.append(conn)

    for d in dead:
        if d in connections:
            connections.remove(d)

    if not connections:
        room_connections.pop(room_id, None)


# =========================================
# BROADCAST ONLINE USERS
# =========================================
async def broadcast_online_users():
    payload = {
        "event": "online_users",
        "user_ids": list(online_users),
    }

    for _, conns in list(user_connections.items()):
        for conn in list(conns):
            try:
                await conn.send_json(payload)
            except:
                pass


# =========================================
# MARK DELIVERED
# =========================================
async def mark_message_delivered(message_id: int):
    db = SessionLocal()
    try:
        msg = db.query(models.ChatMessage).filter(
            models.ChatMessage.id == message_id
        ).first()

        if msg:
            msg.delivered = True
            db.commit()

    except Exception as e:
        db.rollback()
        print("❌ deliver error:", e)

    finally:
        db.close()


# =========================================
# MARK SEEN
# =========================================
async def mark_message_seen(message_id: int):
    db = SessionLocal()
    try:
        msg = db.query(models.ChatMessage).filter(
            models.ChatMessage.id == message_id
        ).first()

        if msg:
            msg.seen = True
            msg.is_read = True
            db.commit()

    except Exception as e:
        db.rollback()
        print("❌ seen error:", e)

    finally:
        db.close()