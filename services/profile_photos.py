"""Validation and local persistence for player profile photos."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from settings import PROFILE_PHOTO_DIR, PROFILE_PHOTO_MAX_BYTES


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
    """Validate an upload and return its generated relative filename."""
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

    PROFILE_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (PROFILE_PHOTO_DIR / filename).write_bytes(content)
    return filename


def remove_profile_photo(filename):
    """Remove an upload after a failed database transaction."""
    if not filename:
        return
    path = PROFILE_PHOTO_DIR / Path(filename).name
    path.unlink(missing_ok=True)
