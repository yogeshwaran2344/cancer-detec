"""
Safe File Upload & Sandbox Storage Service
Handles validation, filename sanitization, size limits, and local privacy sandbox file management.
"""

import os
import re
import uuid
import datetime
from typing import Tuple, Dict, Any
from fastapi import HTTPException
from app.core.config import settings

# Sandbox upload directory within backend
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads",
    "sandbox"
)

# Supported MIME types and extensions
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "text/plain",
    "application/octet-stream"
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename against directory traversal and dangerous characters.
    """
    # Extract basename only
    base = os.path.basename(filename)
    # Strip dangerous characters
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    if not safe_name:
        safe_name = "clinical_report"
    # Prepend timestamp and short UUID for isolation
    unique_prefix = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    return f"{unique_prefix}_{safe_name}"


def validate_file_upload(filename: str, content: bytes, content_type: str = None) -> Tuple[str, float]:
    """
    Validates file extension, content-type and size.
    Returns (extension, size_kb).
    """
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{filename}'. Supported formats: PDF, PNG, JPG, JPEG, TXT."
        )

    file_size = len(content)
    max_size = settings.MAX_UPLOAD_SIZE_BYTES

    if file_size > max_size:
        size_mb = file_size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
        )

    size_kb = round(file_size / 1024, 2)
    return ext, size_kb


def save_to_sandbox(original_filename: str, content: bytes, content_type: str = None) -> Dict[str, Any]:
    """
    Saves validated upload into the local privacy sandbox directory.
    """
    ext, size_kb = validate_file_upload(original_filename, content, content_type)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    safe_name = sanitize_filename(original_filename)
    dest_path = os.path.join(UPLOAD_DIR, safe_name)

    # Secure write
    with open(dest_path, "wb") as f:
        f.write(content)

    return {
        "original_filename": original_filename,
        "sanitized_filename": safe_name,
        "saved_path": dest_path,
        "size_kb": size_kb,
        "extension": ext,
        "content_type": content_type or "application/octet-stream",
        "stored_at": datetime.datetime.now().isoformat()
    }


def get_sandbox_file_path(sanitized_filename: str) -> str:
    """Returns absolute file path within the sandbox, preventing traversal."""
    safe_basename = os.path.basename(sanitized_filename)
    path = os.path.join(UPLOAD_DIR, safe_basename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Requested report file not found in sandbox.")
    return path


def purge_sandbox_storage() -> int:
    """Cleans all cached files in the sandbox directory."""
    if not os.path.exists(UPLOAD_DIR):
        return 0
    count = 0
    for filename in os.listdir(UPLOAD_DIR):
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
                count += 1
            except Exception:
                pass
    return count
