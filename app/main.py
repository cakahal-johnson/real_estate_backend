# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from app.core.config import settings
from app.database import Base, engine

from app.routers import (
    listings,
    users,
    auth,
    favorites,
    admin,
    orders,
    chat,
    cart,
    paystack,
    support,
    recent_views,
)

from app.core.cors import setup_cors
from app.core.errors import add_exception_handlers
from app.core.rate_limit import RateLimitMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.security import decode_access_token

from app.websocket_manager import (
    connect_user,
    disconnect_user,
    send_personal_message,
)

app = FastAPI(title="RealEstateHub API")

# Create DB tables
Base.metadata.create_all(bind=engine)

# =========================
# RATE LIMIT
# =========================
if settings.ENV != "production":
    print("⚠️ Rate limit disabled in development mode")
else:
    app.add_middleware(RateLimitMiddleware, limit=100, window=60)

# =========================
# CORE SETUP
# =========================
setup_cors(app)
add_exception_handlers(app)

# =========================
# ROUTERS
# =========================
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(favorites.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(chat.router)

app.include_router(paystack.router)
app.include_router(support.router)
app.include_router(recent_views.router)
app.include_router(cart.router)

# Static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def root():
    return {"message": "🏡 RealEstateHub API is running ✅"}


# =========================================================
# 🔌 GLOBAL USER WEBSOCKET (ONLINE STATUS + TYPING)
# =========================================================
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...)
):
    """
    Secure global websocket:
    - online presence
    - typing indicators
    - ping/pong
    """

    # =========================
    # AUTH SECURITY CHECK
    # =========================
    try:
        payload = decode_access_token(token)
        if not payload or payload.get("user_id") != user_id:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    # =========================
    # CONNECT USER
    # =========================
    await connect_user(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            # =========================
            # TYPING EVENT
            # =========================
            if event == "typing":
                receiver_id = data.get("receiver_id")

                if receiver_id:
                    await send_personal_message(
                        receiver_id,
                        {
                            "event": "typing",
                            "user_id": user_id
                        }
                    )

            # =========================
            # STOP TYPING EVENT
            # =========================
            elif event == "stop_typing":
                receiver_id = data.get("receiver_id")

                if receiver_id:
                    await send_personal_message(
                        receiver_id,
                        {
                            "event": "stop_typing",
                            "user_id": user_id
                        }
                    )

            # =========================
            # PING / HEARTBEAT
            # =========================
            elif event == "ping":
                await websocket.send_json({
                    "event": "pong"
                })

    # =========================
    # CLEAN DISCONNECT
    # =========================
    except WebSocketDisconnect:
        await disconnect_user(user_id, websocket)

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await disconnect_user(user_id, websocket)