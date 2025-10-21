from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import status


def add_exception_handlers(app):
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": str(exc)}
        )
