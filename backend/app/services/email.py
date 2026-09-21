from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from ..core.config import settings
from .email_templates import render_email

logger = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    pass


def smtp_configured() -> bool:
    return bool(settings.smtp_user and settings.smtp_password and (settings.smtp_from_email or settings.smtp_user))


def send_email(*, kind: str, to_email: str, context: dict) -> None:
    if not smtp_configured():
        logger.warning("SMTP is not configured; skipping outbound email")
        raise EmailNotConfigured("SMTP is not configured")

    subject, html, text = render_email(kind, **context)
    from_email = settings.smtp_from_email or settings.smtp_user
    from_header = f"{settings.smtp_from_name} <{from_email}>" if settings.smtp_from_name else from_email

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_header
    message["To"] = to_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as client:
        if settings.smtp_use_tls:
            client.starttls()
        client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(message)
    logger.info("Outbound email queued/sent template=%s", kind)
