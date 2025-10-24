# app/core/cors.py
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app):
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.0.75:3000",  # optional if testing from LAN
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

