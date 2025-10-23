# app/core/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 30, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        timestamps = [t for t in self.requests[client_ip] if now - t < self.window]
        self.requests[client_ip] = timestamps

        if len(timestamps) >= self.limit:
            raise HTTPException(status_code=429, detail="Too many requests — slow down")

        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response
