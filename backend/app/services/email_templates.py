from __future__ import annotations

import logging
from html import escape

from ..core.config import settings

logger = logging.getLogger(__name__)

BRAND_BG = "#0b1b33"
BRAND_ACCENT = "#2563eb"
BRAND_MUTED = "#64748b"


def _layout(*, title: str, body_html: str, preheader: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;">{escape(preheader)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f7fb;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0;">
          <tr>
            <td style="background:{BRAND_BG};color:#ffffff;padding:28px 28px 24px;">
              <p style="margin:0 0 8px;font-size:12px;letter-spacing:0.08em;color:#93c5fd;">AI LIFE ASSISTANT</p>
              <h1 style="margin:0;font-size:22px;line-height:1.3;">{escape(title)}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;color:#0f172a;font-size:15px;line-height:1.6;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 28px;color:{BRAND_MUTED};font-size:12px;line-height:1.5;">
              This message was sent by AI Life Assistant. If you did not expect it, you can ignore this email.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _otp_block(otp: str) -> str:
    return (
        f'<p style="margin:20px 0 8px;font-size:13px;color:{BRAND_MUTED};">Your OTP is:</p>'
        f'<p style="margin:0;font-size:32px;letter-spacing:0.28em;font-weight:700;color:{BRAND_ACCENT};">{escape(otp)}</p>'
    )


def account_created_email(*, name: str) -> tuple[str, str, str]:
    subject = "Your Account Creation Is Successful"
    greeting = escape(name or "there")
    html = _layout(
        title=subject,
        preheader="Your AI Life Assistant account was created successfully.",
        body_html=(
            f"<p>Hi {greeting},</p>"
            "<p>Your AI Life Assistant account was created successfully.</p>"
            "<p>Please verify your email with the separate verification code we send so you can keep your account secure.</p>"
        ),
    )
    text = (
        f"Hi {name or 'there'},\n\n"
        "Your AI Life Assistant account was created successfully.\n"
        "Please verify your email with the separate verification code we send.\n"
    )
    return subject, html, text


def verification_otp_email(*, name: str, otp: str, expiry_minutes: int) -> tuple[str, str, str]:
    subject = "Verify Your AI Life Assistant Account"
    greeting = escape(name or "there")
    html = _layout(
        title=subject,
        preheader="Use this code to verify your account.",
        body_html=(
            f"<p>Hi {greeting},</p>"
            "<p>Enter this code to verify your AI Life Assistant account.</p>"
            f"{_otp_block(otp)}"
            f"<p style=\"margin-top:20px;\">This OTP expires in {expiry_minutes} minutes. Do not share it with anyone.</p>"
            "<p>If you did not create this account, you can ignore this email.</p>"
        ),
    )
    text = (
        f"Hi {name or 'there'},\n\n"
        f"Your verification OTP is: {otp}\n"
        f"This OTP expires in {expiry_minutes} minutes.\n"
        "If you did not create this account, ignore this email.\n"
    )
    return subject, html, text


def password_reset_otp_email(*, name: str, otp: str, expiry_minutes: int) -> tuple[str, str, str]:
    subject = "Your AI Life Assistant password reset OTP"
    greeting = escape(name or "there")
    html = _layout(
        title="Reset your password",
        preheader="Use this one-time code to reset your password.",
        body_html=(
            f"<p>Hi {greeting},</p>"
            "<p>Use this one-time code to reset your AI Life Assistant password.</p>"
            f"{_otp_block(otp)}"
            f"<p style=\"margin-top:20px;\">This OTP expires in {expiry_minutes} minutes. Do not share it with anyone.</p>"
            "<p>If you did not request a password reset, ignore this email. Your password will stay the same.</p>"
        ),
    )
    text = (
        f"Hi {name or 'there'},\n\n"
        f"Your OTP is: {otp}\n"
        f"This OTP expires in {expiry_minutes} minutes.\n"
        "If you did not request a password reset, ignore this email.\n"
    )
    return subject, html, text


def render_email(kind: str, **context: object) -> tuple[str, str, str]:
    expiry = int(context.get("expiry_minutes") or settings.otp_expiry_minutes)
    name = str(context.get("name") or "")
    otp = str(context.get("otp") or "")
    if kind == "account_created":
        return account_created_email(name=name)
    if kind == "account_verification":
        return verification_otp_email(name=name, otp=otp, expiry_minutes=expiry)
    if kind == "password_reset":
        return password_reset_otp_email(name=name, otp=otp, expiry_minutes=expiry)
    raise ValueError("Unknown email template")
