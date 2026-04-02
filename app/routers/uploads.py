# app/routers/uploads.py

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import Dict
from app.utils.file_handler import save_upload_file
from app.core.security import get_current_active_user
from app import models

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Upload a single image and return its public URL.

    Only accepts JPEG, PNG, and WEBP image formats.
    """
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files (jpg, png, webp) are allowed"
        )

    try:
        file_url = save_upload_file(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )

    return {"url": file_url}


@router.post("/file", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Upload any general file and return its public URL.

    This route allows any file type but still requires authentication.
    """
    try:
        file_url = save_upload_file(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )

    return {"file_url": file_url}
