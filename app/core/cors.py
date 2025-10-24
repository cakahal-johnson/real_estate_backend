# app/core/cors.py ✅ FIX
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ],
        allow_credentials=False,  # ✅ Changed
        allow_methods=["*"],
        allow_headers=["*"],       # ✅ Authorization allowed
        expose_headers=["*"]
    )
