"""Validation for profile photos persisted with the player record."""

from uuid import uuid4

from fastapi import HTTPException, UploadFile

from settings import PROFILE_PHOTO_MAX_BYTES


PHOTO_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"RIFF", ".webp")
)


def _detect_extension(content):
    """Recognize only browser-safe raster formats from their file signatures."""
    for signature, extension in PHOTO_SIGNATURES:
        if content.startswith(signature):
            if extension != ".webp" or content[8:12] == b"WEBP":
                return extension
    return None


async def save_profile_photo(upload: UploadFile):
    """Validate an upload and return persistence-ready image data."""
    content = await upload.read(PROFILE_PHOTO_MAX_BYTES + 1)
    if len(content) > PROFILE_PHOTO_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="La foto no puede exceder 5 MB"
        )

    extension = _detect_extension(content)
    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="La foto debe ser JPG, PNG o WebP"
        )

    filename = f"{uuid4().hex}{extension}"
    media_type = {
        ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"
    }[extension]
    return {"filename": filename, "content": content, "media_type": media_type}


def remove_profile_photo(_photo):
    """Retained as a no-op because failed transactions persist no image."""
