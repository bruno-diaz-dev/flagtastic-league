"""Validation for profile photos persisted with the player record."""

from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from settings import PROFILE_PHOTO_MAX_BYTES, TEAM_LOGO_MAX_BYTES


PHOTO_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"RIFF", ".webp")
)
MEDIA_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
PIL_FORMATS = {".jpg": "JPEG", ".png": "PNG", ".webp": "WEBP"}

# Largest image decoded at all. Checked from the header before decoding, so a
# small, highly compressed file cannot expand into gigabytes of pixels.
MAX_IMAGE_PIXELS = 40_000_000
# Pillow raises DecompressionBombError at twice this value for any decode,
# including the logo thumbnailer and the referee OCR fallback.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
# Stored profile photos never need more than this on their longest side.
PROFILE_PHOTO_MAX_SIDE = 1600

DECODE_ERRORS = (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError)


def _detect_extension(content):
    """Recognize only browser-safe raster formats from their file signatures."""
    for signature, extension in PHOTO_SIGNATURES:
        if content.startswith(signature):
            if extension != ".webp" or content[8:12] == b"WEBP":
                return extension
    return None


def image_too_large(content):
    """Whether the header declares more pixels than MAX_IMAGE_PIXELS.

    Returns None when the content cannot be identified as an image.
    """
    try:
        with Image.open(BytesIO(bytes(content))) as image:
            width, height = image.size
    except DECODE_ERRORS:
        return None
    return width * height > MAX_IMAGE_PIXELS


def _clean_profile_photo(content, extension):
    """Decode and re-encode a photo, dropping EXIF/GPS and other metadata.

    Photos of minors are public, and phone cameras embed the location where
    a picture was taken. Re-encoding keeps only the pixels (and the colour
    profile), applies the camera orientation and bounds the stored size.
    """
    pil_format = PIL_FORMATS[extension]
    try:
        with Image.open(BytesIO(content)) as source:
            width, height = source.size
            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="La foto tiene demasiados pixeles")
            source.load()
            icc_profile = source.info.get("icc_profile")
            image = ImageOps.exif_transpose(source)
            image.thumbnail(
                (PROFILE_PHOTO_MAX_SIDE, PROFILE_PHOTO_MAX_SIDE),
                Image.Resampling.LANCZOS
            )
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            if pil_format == "JPEG":
                image = image.convert("RGB")
            elif image.mode not in ("RGB", "RGBA", "L", "LA") or (pil_format == "WEBP" and image.mode in ("L", "LA")):
                image = image.convert("RGBA" if has_alpha else "RGB")
            image.info = {}
            options = {"exif": b""}
            if icc_profile:
                options["icc_profile"] = icc_profile
            if pil_format == "JPEG":
                options.update(quality=90, optimize=True)
            elif pil_format == "WEBP":
                options.update(quality=90)
            else:
                options.update(optimize=True)
            output = BytesIO()
            image.save(output, format=pil_format, **options)
            return output.getvalue()
    except HTTPException:
        raise
    except DECODE_ERRORS as error:
        raise HTTPException(
            status_code=415,
            detail="La foto debe ser JPG, PNG o WebP"
        ) from error


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

    cleaned = _clean_profile_photo(content, extension)
    filename = f"{uuid4().hex}{extension}"
    return {"filename": filename, "content": cleaned, "media_type": MEDIA_TYPES[extension]}


async def save_team_logo(upload: UploadFile):
    """Validate a team logo using the same safe raster allowlist.

    The original file is kept as uploaded (display copies are derived from
    it), but an image whose dimensions exceed MAX_IMAGE_PIXELS is rejected so
    it can never reach the thumbnailer.
    """
    content = await upload.read(TEAM_LOGO_MAX_BYTES + 1)
    if len(content) > TEAM_LOGO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="El logo no puede exceder 5 MB")

    extension = _detect_extension(content)
    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="El logo debe ser JPG, PNG o WebP"
        )
    if image_too_large(content):
        raise HTTPException(status_code=413, detail="El logo tiene demasiados pixeles")

    return {"content": content, "media_type": MEDIA_TYPES[extension]}


def remove_profile_photo(_photo):
    """Retained as a no-op because failed transactions persist no image."""
