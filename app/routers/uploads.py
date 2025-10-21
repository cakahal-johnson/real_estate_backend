# app/routers/uploads.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import Dict
from app.utils.file_handler import save_upload_file
from app.core.security import get_current_active_user

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
def upload_image(
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user)
):
    """Upload a single image and return its file URL."""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files (jpg, png, webp) are allowed")

    file_url = save_upload_file(file)
    return {"url": file_url}
