# app/utils/file_handler.py
import os
from fastapi import UploadFile
from uuid import uuid4

UPLOAD_DIR = "uploads"


def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file locally and return file URL/path."""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    file_ext = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())

    # return relative or full path
    return f"/{UPLOAD_DIR}/{unique_filename}"
