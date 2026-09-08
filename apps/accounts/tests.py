import time

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import User
from apps.accounts.verification import verification_token_generator


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


class RegisterVerificationTest(TestCase):
    def _wait_for_email(self, timeout=2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if mail.outbox:
                return True
            time.sleep(0.01)
        return False

    def _register(self, email="novo@example.com"):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("accounts:register"),
                {
                    "name": "Cliente Novo",
                    "email": email,
                    "phone": "",
                    "password1": "senha-forte-123",
                    "password2": "senha-forte-123",
                },
            )

    def test_register_creates_inactive_user_and_queues_email(self):
        mail.outbox.clear()
        response = self._register()
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        user = User.objects.get(email="novo@example.com")
        self.assertFalse(user.is_active)
        self.assertIsNone(user.email_verified_at)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(self._wait_for_email(), "e-mail não foi enviado a tempo")
        message = mail.outbox[0]
        self.assertEqual(message.to, ["novo@example.com"])
        self.assertIn("/verify-email/", message.body)

    def test_register_rejects_invalid_email(self):
        response = self._register(email="nao-email")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="nao-email").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_login_before_verification_redirects_to_resend(self):
        self._register()
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "novo@example.com", "password": "senha-forte-123"},
        )
        self.assertRedirects(response, reverse("accounts:resend_verification"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_verify_email_activates_and_logs_in(self):
        self._register()
        user = User.objects.get(email="novo@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = verification_token_generator.make_token(user)
        response = self.client.get(
            reverse("accounts:verify_email", args=[uid, token])
        )
        self.assertRedirects(response, reverse("website:home"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.email_verified_at)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(user.pk))

    def test_verify_email_invalid_token(self):
        self._register()
        user = User.objects.get(email="novo@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse("accounts:verify_email", args=[uid, "invalido"])
        )
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_verify_email_twice_redirects_to_login(self):
        self._register()
        user = User.objects.get(email="novo@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = verification_token_generator.make_token(user)
        url = reverse("accounts:verify_email", args=[uid, token])
        self.client.get(url)
        response = self.client.get(url)
        self.assertRedirects(response, reverse("accounts:login"))

    def test_resend_is_neutral_and_throttled(self):
        mail.outbox.clear()
        self._register()
        self.assertTrue(self._wait_for_email())
        first_count = len(mail.outbox)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("accounts:resend_verification"),
                {"email": "novo@example.com"},
            )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        deadline = time.time() + 2.0
        while time.time() < deadline and len(mail.outbox) <= first_count:
            time.sleep(0.01)
        second_count = len(mail.outbox)
        self.assertGreater(second_count, first_count)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("accounts:resend_verification"),
                {"email": "novo@example.com"},
            )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        time.sleep(0.5)
        self.assertEqual(len(mail.outbox), second_count)
        response = self.client.post(
            reverse("accounts:resend_verification"),
            {"email": "ninguem@example.com"},
        )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        time.sleep(0.2)
        self.assertEqual(len(mail.outbox), second_count)


class ProfilePasswordTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="senha@example.com",
            password="senha-forte-123",
            name="Cliente Senha",
        )
        self.client.force_login(self.user)
        self.url = reverse("accounts:profile_password")

    def test_change_password_success(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "senha-forte-123",
                "new_password1": "nova-senha-456",
                "new_password2": "nova-senha-456",
            },
        )
        self.assertRedirects(
            response, reverse("accounts:profile") + "?tab=password"
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("nova-senha-456"))
        self.assertIn("_auth_user_id", self.client.session)
        response = self.client.get(reverse("accounts:profile") + "?tab=password")
        self.assertContains(response, "Senha alterada com sucesso.")

    def test_wrong_current_password_rejected(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "errada",
                "new_password1": "nova-senha-456",
                "new_password2": "nova-senha-456",
            },
        )
        self.assertRedirects(
            response, reverse("accounts:profile") + "?tab=password"
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("senha-forte-123"))

    def test_mismatched_passwords_rejected(self):
        self.client.post(
            self.url,
            {
                "current_password": "senha-forte-123",
                "new_password1": "nova-senha-456",
                "new_password2": "outra-senha-789",
            },
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("senha-forte-123"))

    def test_weak_password_rejected(self):
        self.client.post(
            self.url,
            {
                "current_password": "senha-forte-123",
                "new_password1": "123",
                "new_password2": "123",
            },
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("senha-forte-123"))

    def test_get_redirects_to_password_tab(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response, reverse("accounts:profile") + "?tab=password"
        )

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        response = self.client.post(
            self.url,
            {
                "current_password": "senha-forte-123",
                "new_password1": "nova-senha-456",
                "new_password2": "nova-senha-456",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_password_tab_renders(self):
        response = self.client.get(reverse("accounts:profile") + "?tab=password")
        self.assertContains(response, "Trocar senha")
        self.assertContains(response, 'name="current_password"')


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

    def test_profile_data_rejects_invalid_check_digits(self):
        self.client.post(
            reverse("accounts:profile_data"),
            {"name": "Nome Novo", "phone": "", "cpf": "12345678900"},
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.cpf, "")
    def test_profile_data_saves_birth_date(self):
        self.client.post(
            reverse("accounts:profile_data"),
            {
                "name": "Nome Novo",
                "phone": "",
                "cpf": "",
                "birth_date": "1990-05-15",
            },
        )

        self.user.refresh_from_db()
        self.assertEqual(str(self.user.birth_date), "1990-05-15")

    def test_profile_data_rejects_future_birth_date(self):
        self.client.post(
            reverse("accounts:profile_data"),
            {
                "name": "Nome Novo",
                "phone": "",
                "cpf": "",
                "birth_date": "2999-01-01",
            },
        )

        self.user.refresh_from_db()
        self.assertIsNone(self.user.birth_date)
        self.assertEqual(self.user.name, "Nome Antigo")

    def test_profile_data_rejects_invalid_birth_date(self):
        self.client.post(
            reverse("accounts:profile_data"),
            {
                "name": "Nome Novo",
                "phone": "",
                "cpf": "",
                "birth_date": "31/02/2000",
            },
        )

        self.user.refresh_from_db()
        self.assertIsNone(self.user.birth_date)

    def test_profile_data_allows_blank_birth_date(self):
        self.client.post(
            reverse("accounts:profile_data"),
            {"name": "Nome Novo", "phone": "", "cpf": "", "birth_date": ""},
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Nome Novo")
        self.assertIsNone(self.user.birth_date)
