import time

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
        mail.outbox.clear()

    def _wait_for_email(self, timeout=2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if mail.outbox:
                return True
            time.sleep(0.01)
        return False

    def test_password_reset_sends_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertTrue(self._wait_for_email(), "e-mail não foi enviado a tempo")
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

        time.sleep(0.1)
        self.assertEqual(len(mail.outbox), 0)


class ProfileDataTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cpf@example.com",
            password="senha-forte-123",
            name="Nome Antigo",
        )
        self.client.force_login(self.user)

    def test_profile_data_saves_name_phone_and_cpf(self):
        response = self.client.post(
            reverse("accounts:profile_data"),
            {"name": "Nome Novo", "phone": "(11) 99999-9999", "cpf": "123.456.789-09"},
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Nome Novo")
        self.assertEqual(self.user.phone, "(11) 99999-9999")
        self.assertEqual(self.user.cpf, "12345678909")

    def test_profile_data_rejects_invalid_cpf(self):
        self.client.post(
            reverse("accounts:profile_data"),
            {"name": "Nome Novo", "phone": "", "cpf": "123"},
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Nome Antigo")
        self.assertEqual(self.user.cpf, "")