from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class PasswordResetEmailTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cliente@example.com",
            password="senha-forte-123",
            name="Cliente Teste",
        )

    def test_password_reset_sends_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.user.email])
        self.assertTrue(message.subject.startswith("Redefinição de senha"))
        self.assertIn("/reset/", message.body)
        self.assertIn("Olá Cliente Teste", message.body)

    def test_password_reset_unknown_email_sends_nothing(self):
        self.client.post(
            reverse("accounts:password_reset"),
            {"email": "nao-existe@example.com"},
        )

        self.assertEqual(len(mail.outbox), 0)