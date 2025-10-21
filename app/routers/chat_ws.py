from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from typing import Dict, List

router = APIRouter(prefix="/ws", tags=["Chat WebSocket"])

active_connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/{room_id}")
async def chat_room(websocket: WebSocket, room_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = models.ChatMessage(room_id=room_id, message=data)
            db.add(message)
            db.commit()
            db.refresh(message)

            for conn in active_connections[room_id]:
                await conn.send_text(f"{message.created_at} — {message.message}")

    except WebSocketDisconnect:
        active_connections[room_id].remove(websocket)
