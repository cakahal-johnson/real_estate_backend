# app/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, List
from app.database import SessionLocal
from app import models

active_connections: Dict[int, List[WebSocket]] = {}
online_users: set[int] = set()


async def connect_user(user_id: int, websocket: WebSocket):
    await websocket.accept()
    if user_id not in active_connections:
        active_connections[user_id] = []
    active_connections[user_id].append(websocket)
    online_users.add(user_id)
    print(f"✅ User {user_id} connected")
    await broadcast_user_status(user_id, "online")


async def disconnect_user(user_id: int, websocket: WebSocket):
    if user_id in active_connections:
        active_connections[user_id].remove(websocket)
        if not active_connections[user_id]:
            del active_connections[user_id]
            online_users.discard(user_id)
            await broadcast_user_status(user_id, "offline")
    print(f"❌ User {user_id} disconnected")


async def send_personal_message(user_id: int, message: dict):
    """Send message to a specific connected user."""
    if user_id in active_connections:
        for conn in active_connections[user_id]:
            await conn.send_json(message)


async def broadcast_user_status(user_id: int, status: str):
    """Notify all users when someone goes online/offline."""
    payload = {"event": "user_status", "user_id": user_id, "status": status}
    for conns in active_connections.values():
        for conn in conns:
            await conn.send_json(payload)


async def broadcast_online_users():
    """Send list of all online users to everyone."""
    payload = {"event": "online_users", "user_ids": list(online_users)}
    for conns in active_connections.values():
        for conn in conns:
            await conn.send_json(payload)


async def mark_message_delivered(message_id: int):
    """Mark message as delivered in DB."""
    db = SessionLocal()
    msg = db.query(models.Message).filter(models.Message.id == message_id).first()
    if msg:
        msg.delivered = True
        db.commit()
    db.close()


async def mark_message_seen(message_id: int):
    """Mark message as seen in DB."""
    db = SessionLocal()
    msg = db.query(models.Message).filter(models.Message.id == message_id).first()
    if msg:
        msg.seen = True
        db.commit()
    db.close()
