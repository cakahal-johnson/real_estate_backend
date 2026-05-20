# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database import Base, engine

# ROUTERS
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

# CORE
from app.core.cors import setup_cors
from app.core.errors import add_exception_handlers
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import decode_access_token

# WEBSOCKET
from app.websocket_manager import (
    connect_user,
    disconnect_user,
    send_personal_message,
)

# =========================
# APP INIT
# =========================
app = FastAPI(title="RealEstateHub API")

# =========================
# DB INIT
# =========================
Base.metadata.create_all(bind=engine)

# =========================
# MIDDLEWARE
# =========================
if settings.ENV == "production":
    app.add_middleware(RateLimitMiddleware, limit=100, window=60)
else:
    print("⚠️ Rate limit disabled in development mode")

setup_cors(app)
add_exception_handlers(app)

# =========================
# ROUTER REGISTRATION
# =========================
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(favorites.router)

# ⭐ ADMIN SYSTEM (FULL SERVICE CONNECTED HERE)
app.include_router(admin.router)

app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(cart.router)
app.include_router(paystack.router)
app.include_router(support.router)
app.include_router(recent_views.router)

# =========================
# STATIC FILES
# =========================
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"message": "🏡 RealEstateHub API is running ✅"}


# =========================================================
# 🔌 GLOBAL WEBSOCKET SYSTEM
# =========================================================
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...)
):

    # =========================
    # AUTH VALIDATION
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
            # TYPING
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
            # STOP TYPING
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
            # HEARTBEAT
            # =========================
            elif event == "ping":
                await websocket.send_json({"event": "pong"})

    # =========================
    # DISCONNECT CLEANUP
    # =========================
    except WebSocketDisconnect:
        await disconnect_user(user_id, websocket)

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await disconnect_user(user_id, websocket)