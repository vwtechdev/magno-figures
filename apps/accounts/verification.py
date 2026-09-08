import logging

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.mail import send_mail_async
from core.utils import site_base_url

logger = logging.getLogger(__name__)

VERIFICATION_RESEND_TIMEOUT = 300


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "apps.accounts.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return (
            f"{user.pk}{user.email}{user.is_active}"
            f"{user.email_verified_at}{user.password}{timestamp}"
        )


verification_token_generator = EmailVerificationTokenGenerator()


def build_verification_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = verification_token_generator.make_token(user)
    path = reverse("accounts:verify_email", args=[uid, token])
    return site_base_url() + path


def verification_email_body(user, verification_url):
    return (
        f"Olá, {user.name}!\n\n"
        "Obrigado por criar sua conta na Magno Figures.\n\n"
        "Confirme seu e-mail clicando no link abaixo:\n"
        f"{verification_url}\n\n"
        "O link expira em 48 horas.\n\n"
        "Se você não criou esta conta, ignore esta mensagem."
    )


def send_verification_email(user):
    verification_url = build_verification_url(user)
    subject = "Confirme seu e-mail — Magno Figures"
    body = verification_email_body(user, verification_url)

    def _dispatch():
        send_mail_async(
            subject,
            body,
            [user.email],
            from_email=settings.DEFAULT_FROM_EMAIL,
        )

    transaction.on_commit(_dispatch)


def resend_throttled(user):
    key = f"email-verify:{user.pk}"
    if cache.get(key):
        return True
    cache.set(key, 1, VERIFICATION_RESEND_TIMEOUT)
    return False
