"""Persistence and read models for team inscription payments."""

from decimal import Decimal, ROUND_HALF_UP

from database import get_connection


def pesos_to_cents(amount):
    """Convert a validated peso amount to integer cents."""
    return int((Decimal(amount) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_pesos(cents):
    return float(Decimal(cents or 0) / Decimal(100))


def list_admin_team_balances():
    """Return every team with inscription fee, paid amount and payment history."""
    connection = get_connection()
    teams = connection.execute(
        """
        SELECT teams.id, teams.name, teams.branch, teams.category, teams.status,
               teams.registration_fee_cents,
               COALESCE(SUM(team_payments.amount_cents), 0)::INTEGER AS paid_cents
        FROM teams
        LEFT JOIN team_payments ON team_payments.team_id = teams.id
        GROUP BY teams.id
        ORDER BY
            CASE teams.branch
                WHEN 'varonil' THEN 1
                WHEN 'femenil' THEN 2
                WHEN 'mixto' THEN 3
                ELSE 4
            END,
            CASE teams.category
                WHEN 'u6' THEN 1
                WHEN 'u8' THEN 2
                WHEN 'u10' THEN 3
                WHEN 'u12' THEN 4
                WHEN 'u14' THEN 5
                WHEN 'u16' THEN 6
                WHEN 'u18' THEN 7
                WHEN 'libre' THEN 8
                ELSE 9
            END,
            LOWER(teams.name),
            teams.id
        """
    ).fetchall()
    payments = connection.execute(
        """
        SELECT team_payments.id, team_payments.team_id,
               team_payments.amount_cents, team_payments.method,
               team_payments.receiver_name, team_payments.reference,
               team_payments.notes, team_payments.proof_filename,
               team_payments.recorded_by_user_id,
               users.name AS recorded_by_name,
               team_payments.received_at, team_payments.created_at
        FROM team_payments
        LEFT JOIN users ON users.id = team_payments.recorded_by_user_id
        ORDER BY team_payments.received_at DESC, team_payments.id DESC
        """
    ).fetchall()
    connection.close()
    return _teams_with_payments(teams, payments)


def get_representative_team_finances(team_ids):
    """Return payment summaries for a representative's assigned teams."""
    if not team_ids:
        return {}
    connection = get_connection()
    teams = connection.execute(
        """
        SELECT teams.id, teams.registration_fee_cents,
               COALESCE(SUM(team_payments.amount_cents), 0)::INTEGER AS paid_cents
        FROM teams
        LEFT JOIN team_payments ON team_payments.team_id = teams.id
        WHERE teams.id = ANY(%s)
        GROUP BY teams.id
        """,
        (team_ids,)
    ).fetchall()
    payments = connection.execute(
        """
        SELECT id, team_id, amount_cents, method, receiver_name, reference,
               notes, proof_filename, recorded_by_user_id, NULL AS recorded_by_name,
               received_at, created_at
        FROM team_payments
        WHERE team_id = ANY(%s)
        ORDER BY received_at DESC, id DESC
        """,
        (team_ids,)
    ).fetchall()
    connection.close()
    return {
        team["id"]: team["finance"]
        for team in _teams_with_payments(teams, payments)
    }


def update_team_registration_fee(team_id, amount):
    """Set the amount owed by one team for inscription."""
    connection = get_connection()
    try:
        row = connection.execute(
            """
            UPDATE teams
            SET registration_fee_cents = %s
            WHERE id = %s
            RETURNING id
            """,
            (pesos_to_cents(amount), team_id)
        ).fetchone()
        connection.commit()
        return row is not None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_team_payment(team_id, payment, admin_user, proof=None):
    """Persist one administrator-entered payment for a team."""
    connection = get_connection()
    try:
        row = connection.execute(
            """
            INSERT INTO team_payments (
                team_id, amount_cents, method, receiver_name, reference, notes,
                proof_filename, proof_media_type, proof_data,
                recorded_by_user_id
            )
            SELECT teams.id, %s, %s, %s, %s, %s, %s, %s, %s, users.id
            FROM teams
            LEFT JOIN users ON users.id = %s
            WHERE teams.id = %s
            RETURNING id
            """,
            (
                pesos_to_cents(payment.amount),
                payment.method,
                payment.receiver_name or admin_user.get("display_name") or admin_user.get("name"),
                payment.reference,
                payment.notes,
                proof["filename"] if proof else None,
                proof["media_type"] if proof else None,
                proof["content"] if proof else None,
                admin_user["id"],
                team_id,
            )
        ).fetchone()
        connection.commit()
        return row["id"] if row is not None else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_payment_proof(payment_id):
    """Return one stored proof file, if the payment has one."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT proof_filename, proof_media_type, proof_data
        FROM team_payments
        WHERE id = %s
        """,
        (payment_id,)
    ).fetchone()
    connection.close()
    if row is None or row["proof_data"] is None:
        return None
    return dict(row)


def _teams_with_payments(team_rows, payment_rows):
    payments_by_team = {}
    for raw_payment in payment_rows:
        payment = _public_payment(raw_payment)
        payments_by_team.setdefault(payment.pop("team_id"), []).append(payment)

    result = []
    for raw_team in team_rows:
        team = dict(raw_team)
        registration_fee_cents = team.pop("registration_fee_cents", 0)
        paid_cents = team.pop("paid_cents", 0)
        balance_cents = max(registration_fee_cents - paid_cents, 0)
        team["finance"] = {
            "registration_fee": cents_to_pesos(registration_fee_cents),
            "paid_amount": cents_to_pesos(paid_cents),
            "balance_due": cents_to_pesos(balance_cents),
            "is_paid": balance_cents == 0 and registration_fee_cents > 0,
            "payments": payments_by_team.get(team["id"], []),
        }
        result.append(team)
    return result


def _public_payment(row):
    payment = dict(row)
    payment["amount"] = cents_to_pesos(payment.pop("amount_cents"))
    payment["has_proof"] = payment.pop("proof_filename") is not None
    return payment
