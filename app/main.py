# app/main.py
from fastapi import FastAPI

from app.core.config import settings
from app.database import Base, engine
from app.routers import listings, users, auth, favorites, admin, orders, chat
from app.core.cors import setup_cors
from app.core.errors import add_exception_handlers
from app.core.rate_limit import RateLimitMiddleware


# Create all DB tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RealEstateHub API")


# ✅ Rate limit only in production
if settings.ENV != "production":
    print("⚠️ Rate limit disabled in development mode")
else:
    app.add_middleware(RateLimitMiddleware, limit=100, window=60)

# ✅ CORS + global exception handlers
setup_cors(app)
add_exception_handlers(app)


# ✅ Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(favorites.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "Welcome to RealEstateHub API is Running ✅"}
