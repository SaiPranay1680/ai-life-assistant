import hashlib
import hmac
import secrets
import unittest
from uuid import uuid4

from app.core.config import settings
from app.services.email_templates import render_email


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(*, otp: str, user_id, otp_type: str) -> str:
    material = f"{otp_type}:{user_id}:{otp}".encode("utf-8")
    return hmac.new(settings.jwt_secret.encode("utf-8"), material, hashlib.sha256).hexdigest()


class OtpSecurityTests(unittest.TestCase):
    def test_generate_otp_is_six_digits(self):
        for _ in range(20):
            otp = _generate_otp()
            self.assertEqual(len(otp), 6)
            self.assertTrue(otp.isdigit())

    def test_hash_is_purpose_bound(self):
        user_id = uuid4()
        otp = "483921"
        reset_hash = _hash_otp(otp=otp, user_id=user_id, otp_type="PASSWORD_RESET")
        verify_hash = _hash_otp(otp=otp, user_id=user_id, otp_type="ACCOUNT_VERIFICATION")
        self.assertNotEqual(reset_hash, verify_hash)
        self.assertTrue(hmac.compare_digest(reset_hash, _hash_otp(otp=otp, user_id=user_id, otp_type="PASSWORD_RESET")))
        self.assertFalse(hmac.compare_digest(reset_hash, verify_hash))


class EmailTemplateTests(unittest.TestCase):
    def test_account_created_subject(self):
        subject, html, text = render_email("account_created", name="Ada")
        self.assertEqual(subject, "Your Account Creation Is Successful")
        self.assertIn("created successfully", text.lower())
        self.assertNotIn("483921", html)

    def test_verification_otp_copy(self):
        subject, html, text = render_email(
            "account_verification",
            name="Ada",
            otp="739215",
            expiry_minutes=10,
        )
        self.assertEqual(subject, "Verify Your AI Life Assistant Account")
        self.assertIn("Your verification OTP is: 739215", text)
        self.assertIn("739215", html)
        self.assertIn("10 minutes", text)

    def test_password_reset_otp_copy(self):
        subject, html, text = render_email(
            "password_reset",
            name="Ada",
            otp="483921",
            expiry_minutes=10,
        )
        self.assertIn("Your OTP is: 483921", text)
        self.assertIn("ignore", text.lower())
        self.assertIn("483921", html)
