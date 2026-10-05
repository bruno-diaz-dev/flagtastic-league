"""Small display derivatives; the stored original logo remains unchanged."""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


def thumbnail_logo(content, media_type, size):
    """Return a bounded WebP derivative or the original for legacy invalid data."""
    try:
        with Image.open(BytesIO(bytes(content))) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            image = image.convert("RGBA" if "A" in image.getbands() or image.mode == "P" else "RGB")
            output = BytesIO()
            image.save(output, format="WEBP", quality=82, method=4)
            return output.getvalue(), "image/webp"
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return bytes(content), media_type
