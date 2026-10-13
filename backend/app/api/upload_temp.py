"""
ADAPT — Temporary File Upload API

POST /api/upload/temp — Upload reference files for a generation request
                        Files are stored temporarily and NOT added to permanent KB.
"""

import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.logging import get_logger
from app.database import get_db
from app.models.user import User

logger = get_logger("api.upload_temp")
settings = get_settings()
router = APIRouter(tags=["Temporary Uploads"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


@router.post("/api/upload/temp", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_temp_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload one or more reference files for use in a generation request.
    
    Files are saved to a temporary directory and their paths returned.
    They are NOT permanently indexed — the caller must pass these paths
    to the generation endpoint which handles request-scoped ingestion.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    upload_batch_id = str(uuid.uuid4())
    temp_dir = Path(settings.upload_dir) / "temp" / upload_batch_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            logger.warning(f"Rejected temp upload: {file.filename} (unsupported: {ext})")
            continue

        # Validate file size
        content = await file.read()
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} exceeds max size ({settings.max_upload_size_mb}MB)",
            )

        safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = temp_dir / safe_name

        with open(file_path, "wb") as f:
            f.write(content)

        saved_files.append({
            "original_name": file.filename,
            "saved_path": str(file_path),
            "size_bytes": len(content),
            "extension": ext,
        })
        logger.info(f"Temp file saved: {file.filename} → {file_path}")

    if not saved_files:
        raise HTTPException(status_code=400, detail="No valid files uploaded")

    return {
        "batch_id": upload_batch_id,
        "files": saved_files,
        "file_paths": [f["saved_path"] for f in saved_files],
        "count": len(saved_files),
    }
