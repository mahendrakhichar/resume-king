"""File upload and storage utilities."""

import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile, HTTPException

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024  # Convert MB to bytes


async def save_upload(file: UploadFile, user_id: str) -> tuple[str, str]:
    """
    Save an uploaded file to the local filesystem.

    Returns:
        Tuple of (file_path, file_type)
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )

    # Create user-specific upload directory
    upload_dir = Path(settings.upload_dir) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / unique_name

    # Write file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    logger.info(f"Saved upload: {file.filename} → {file_path} ({len(content)} bytes)")

    file_type = ext.lstrip(".")
    return Path(file_path).as_posix(), file_type


async def delete_file(file_path: str) -> bool:
    """Delete a file from the filesystem."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete {file_path}: {e}")
        return False
