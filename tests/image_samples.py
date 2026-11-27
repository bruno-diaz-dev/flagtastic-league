"""Real, tiny images for upload tests (uploads are decoded and re-encoded)."""

from io import BytesIO

from PIL import Image


def png_bytes(size=(4, 4), color=(20, 120, 200)):
    """A valid PNG of the given size and colour."""
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def jpeg_with_exif(size=(8, 6)):
    """A JPEG carrying EXIF camera and orientation tags, like a phone photo.

    GPS coordinates live in the same EXIF block, so a photo that keeps no
    EXIF at all keeps no location either.
    """
    image = Image.new("RGB", size, (200, 60, 40))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    exif[0x0132] = "2026:11:27 10:00:00"  # DateTime
    exif[0x0112] = 6  # Orientation: rotate 90 degrees clockwise to display
    output = BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def is_image(content, expected_format):
    """Whether bytes decode as an image of the expected Pillow format."""
    with Image.open(BytesIO(content)) as image:
        return image.format == expected_format
