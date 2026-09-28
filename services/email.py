"""Transactional email delivery through the Resend HTTPS API."""

import json
import logging
from urllib import request

from settings import PASSWORD_RESET_FROM_EMAIL, RESEND_API_KEY


logger = logging.getLogger("flagtastic")


def send_password_reset_email(email, reset_url):
    """Send a reset link without logging its secret token."""
    if not RESEND_API_KEY or not PASSWORD_RESET_FROM_EMAIL:
        logger.warning("password_reset.email_not_configured")
        return False

    payload = json.dumps({
        "from": PASSWORD_RESET_FROM_EMAIL,
        "to": [email],
        "subject": "Restablece tu contraseña de Flagtastic League",
        "html": (
            "<p>Recibimos una solicitud para restablecer tu contraseña.</p>"
            f'<p><a href="{reset_url}">Crear una nueva contraseña</a></p>'
            "<p>El enlace vence en 30 minutos y solo puede usarse una vez.</p>"
            "<p>Si no hiciste esta solicitud, puedes ignorar este mensaje.</p>"
        ),
    }).encode("utf-8")
    outgoing = request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(outgoing, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception as error:
        logger.error(
            "password_reset.email_failed",
            extra={"error_type": type(error).__name__},
        )
        return False
