"""Small display derivatives; the stored original logo remains unchanged."""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from services.profile_photos import MAX_IMAGE_PIXELS


def thumbnail_logo(content, media_type, size):
    """Return a bounded WebP derivative or the original for legacy invalid data.

    The pixel count is read from the header first: an oversized logo stored
    before upload validation existed is served unchanged instead of being
    decoded on every cache miss.
    """
    try:
        with Image.open(BytesIO(bytes(content))) as image:
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                return bytes(content), media_type
            image = ImageOps.exif_transpose(image)
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            image = image.convert("RGBA" if "A" in image.getbands() or image.mode == "P" else "RGB")
            output = BytesIO()
            image.save(output, format="WEBP", quality=82, method=4)
            return output.getvalue(), "image/webp"
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return bytes(content), media_type
