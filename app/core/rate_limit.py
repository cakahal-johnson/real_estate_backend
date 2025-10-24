# app/core/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit=100, window=60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # ✅ Paths we should NEVER rate-limit to avoid auth redirect loops
        skip_paths = [
            "/", "/favicon.ico"
        ]
        skip_startswith = [
            "/auth",       # login/register/refresh
            "/users/me",   # validate token
            "/favorites",  # auto fetch favorites
            "/static",
        ]

        # ✅ Allow OPTIONS (CORS preflight) always
        if request.method == "OPTIONS" or path in skip_paths or any(path.startswith(p) for p in skip_startswith):
            return await call_next(request)

        client_ip = request.client.host
        now = time.time()
        window_start = now - self.window

        self.requests.setdefault(client_ip, [])
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        if len(self.requests[client_ip]) >= self.limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests — slow down"
            )

        self.requests[client_ip].append(now)
        return await call_next(request)
