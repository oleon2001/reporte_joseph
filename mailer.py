"""
Envío seguro del correo vía Gmail (SMTP_SSL, puerto 465).
"""
import logging
import os
import smtplib
from email.message import EmailMessage

import config

log = logging.getLogger(__name__)


class MailError(Exception):
    """Error controlado de envío (autenticación, red o SMTP)."""


def _attach(msg, path):
    if not os.path.exists(path):
        raise MailError(f"Adjunto no encontrado: {path}")
    with open(path, "rb") as fh:
        data = fh.read()
    filename = os.path.basename(path)
    lower = filename.lower()
    if lower.endswith(".pdf"):
        maintype, subtype = "application", "pdf"
    elif lower.endswith(".xlsx"):
        maintype, subtype = (
            "application",
            "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        maintype, subtype = "application", "octet-stream"
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)


def build_message(user, subject, body, attachments, recipients=None):
    recipients = recipients or config.RECIPIENTS
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)
    for path in attachments:
        _attach(msg, path)
    return msg


def send_email(user, app_password, subject, body, attachments, recipients=None, dry_run=False):
    """Envía el correo. Devuelve True si se envió, False en dry-run."""
    recipients = recipients or config.RECIPIENTS
    msg = build_message(user, subject, body, attachments, recipients)
    if dry_run:
        log.info("DRY-RUN: correo NO enviado (%d adjuntos)", len(attachments))
        return False
    try:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.login(user, app_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError(
            "Autenticación fallida en Gmail. Verifica la contraseña de aplicación "
            "(no la contraseña normal de la cuenta)."
        ) from exc
    except smtplib.SMTPException as exc:
        raise MailError(
            f"Error SMTP ({config.SMTP_HOST}:{config.SMTP_PORT}): {exc}"
        ) from exc
    except OSError as exc:
        raise MailError(
            f"No se pudo conectar a {config.SMTP_HOST}:{config.SMTP_PORT}. "
            f"Revisa la red interna/salida a internet: {exc}"
        ) from exc
    log.info("Correo enviado a %d destinatarios con %d adjuntos", len(recipients), len(attachments))
    return True


if __name__ == "__main__":
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"%PDF-1.4\n")
        path = tmp.name
    try:
        msg = build_message("x@gmail.com", "Asunto", "Cuerpo", [path])
        assert msg["To"].count("@") == len(config.RECIPIENTS)
        assert len(list(msg.iter_attachments())) == 1
        assert msg.get_content_type() == "multipart/mixed"
    finally:
        os.remove(path)
    print("mailer OK")
