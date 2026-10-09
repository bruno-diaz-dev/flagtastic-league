"""Validation for optional administrator-uploaded payment proofs."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile


PAYMENT_PROOF_MAX_BYTES = 5 * 1024 * 1024
PAYMENT_PROOF_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"%PDF-", ".pdf", "application/pdf"),
)


async def save_payment_proof(upload: UploadFile | None):
    """Validate an optional JPG, PNG or PDF proof for database storage."""
    if upload is None or not upload.filename:
        return None

    content = await upload.read(PAYMENT_PROOF_MAX_BYTES + 1)
    if len(content) > PAYMENT_PROOF_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El comprobante no puede exceder 5 MB",
        )

    for signature, extension, media_type in PAYMENT_PROOF_SIGNATURES:
        if content.startswith(signature):
            original_stem = Path(upload.filename).stem[:40] or "comprobante"
            filename = f"{uuid4().hex}-{original_stem}{extension}"
            return {
                "filename": filename,
                "content": content,
                "media_type": media_type,
            }

    raise HTTPException(
        status_code=415,
        detail="El comprobante debe ser JPG, PNG o PDF",
    )
