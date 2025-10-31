# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
from app.core.config import settings
from app.database import Base, engine
from app.routers import listings, users, auth, favorites, admin, orders, chat, messages
from app.core.cors import setup_cors
from app.core.errors import add_exception_handlers
from app.core.rate_limit import RateLimitMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio

# ✅ Import the new WebSocket manager
from app.websocket_manager import (
    connect_user,
    disconnect_user,
    send_personal_message,
    mark_message_delivered,
    mark_message_seen,
)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="RealEstateHub API")

if settings.ENV != "production":
    print("⚠️ Rate limit disabled in development mode")
else:
    app.add_middleware(RateLimitMiddleware, limit=100, window=60)

setup_cors(app)
add_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(favorites.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(messages.router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def root():
    return {"message": "🏡 RealEstateHub API is running ✅"}



# =====================================
# 🔌 WEBSOCKET HANDLER (Enhanced)
# =====================================
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await connect_user(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "typing":
                receiver_id = data.get("receiver_id")
                await send_personal_message(receiver_id, {"event": "typing", "user_id": user_id})

            elif event == "stop_typing":
                receiver_id = data.get("receiver_id")
                await send_personal_message(receiver_id, {"event": "stop_typing", "user_id": user_id})

            elif event == "delivered":
                message_id = data.get("message_id")
                await mark_message_delivered(message_id)

            elif event == "seen":
                message_id = data.get("message_id")
                await mark_message_seen(message_id)

            elif event == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        await disconnect_user(user_id, websocket)