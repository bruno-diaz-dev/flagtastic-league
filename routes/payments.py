"""Team payment administration and representative read-only balances."""

from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError

from dependencies.auth import require_league_admin
from models import TeamPaymentCreate, TeamRegistrationFeeUpdate
from repositories.payments import (
    create_team_payment,
    get_payment_proof,
    list_admin_team_balances,
    update_team_registration_fee,
)
from services.payment_proofs import save_payment_proof


router = APIRouter(prefix="/api/admin/payments", tags=["payments"])


@router.get("/teams")
def list_team_balances(_admin=Depends(require_league_admin)):
    """List teams with amount owed, payment history and capture metadata."""
    return list_admin_team_balances()


@router.patch("/teams/{team_id}/fee", status_code=204)
def change_registration_fee(
    team_id: int,
    payload: TeamRegistrationFeeUpdate,
    _admin=Depends(require_league_admin),
):
    """Let administrators set or correct one team's inscription amount."""
    if not update_team_registration_fee(team_id, payload.amount):
        raise HTTPException(status_code=404, detail="Equipo no encontrado")


@router.post("/teams/{team_id}/payments", status_code=201)
async def add_team_payment(
    team_id: int,
    amount: Decimal = Form(...),
    method: str = Form(...),
    receiver_name: str | None = Form(default=None),
    reference: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    proof: UploadFile | None = File(default=None),
    admin=Depends(require_league_admin),
):
    """Record a cash or transfer payment entered by an administrator."""
    try:
        payment = TeamPaymentCreate(
            amount=amount,
            method=method,
            receiver_name=receiver_name,
            reference=reference,
            notes=notes,
        )
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error
    payment_id = create_team_payment(
        team_id,
        payment,
        admin,
        proof=await save_payment_proof(proof),
    )
    if payment_id is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return {"id": payment_id}


@router.get("/{payment_id}/proof")
def read_payment_proof(
    payment_id: int,
    _admin=Depends(require_league_admin),
):
    """Serve a stored proof only to league administrators."""
    proof = get_payment_proof(payment_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return Response(
        content=bytes(proof["proof_data"]),
        media_type=proof["proof_media_type"] or "application/octet-stream",
        headers={
            "Content-Disposition": (
                f'inline; filename="{proof["proof_filename"] or "comprobante"}"'
            ),
            "Cache-Control": "private, no-store",
        },
    )
