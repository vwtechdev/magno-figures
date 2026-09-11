import time
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import User
from apps.accounts.recaptcha import verify_recaptcha_token
from apps.accounts.verification import verification_token_generator
from apps.addresses.models import Address
from apps.orders.models import Order, OrderStatus


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
            follow=True,
        )
        self.assertRedirects(
            response, reverse("accounts:profile") + "?tab=password"
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("nova-senha-456"))
        self.assertIn("_auth_user_id", self.client.session)
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


class ProfileDeleteTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="excluir@example.com",
            password="senha-forte-123",
            name="Cliente Excluir",
            phone="(11) 99999-9999",
        )
        self.address = Address.objects.create(
            user=self.user,
            zip_code="01310-100",
            street="Av. Paulista",
            number="1000",
            neighborhood="Bela Vista",
            city="São Paulo",
            state="SP",
        )
        self.client.force_login(self.user)
        self.url = reverse("accounts:profile_delete")
        self.tab_url = reverse("accounts:profile") + "?tab=password"

    def test_delete_without_orders_anonymizes_and_logs_out(self):
        response = self.client.post(self.url, {"password": "senha-forte-123"})
        self.assertRedirects(response, reverse("website:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.name, "Conta excluída")
        self.assertEqual(self.user.phone, "")
        self.assertTrue(self.user.email.startswith("excluido_"))

    def test_wrong_password_rejected(self):
        response = self.client.post(self.url, {"password": "errada"})
        self.assertRedirects(response, self.tab_url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.email, "excluir@example.com")

    def test_open_order_blocks_deletion(self):
        order = Order.objects.create(
            user=self.user, address=self.address, status=OrderStatus.NEW
        )
        response = self.client.post(self.url, {"password": "senha-forte-123"})
        self.assertRedirects(response, self.tab_url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())

    def test_delivered_order_allows_deletion_and_preserves_order(self):
        order = Order.objects.create(
            user=self.user, address=self.address, status=OrderStatus.DELIVERED
        )
        response = self.client.post(self.url, {"password": "senha-forte-123"})
        self.assertRedirects(response, reverse("website:home"))
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        order.refresh_from_db()
        self.assertEqual(order.address.full_address, self.address.full_address)

    def test_get_redirects_to_password_tab(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, self.tab_url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        response = self.client.post(self.url, {"password": "senha-forte-123"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_password_tab_renders_delete_button_and_modal(self):
        response = self.client.get(reverse("accounts:profile") + "?tab=password")
        self.assertContains(response, "Excluir Conta")
        self.assertContains(response, 'id="deleteAccountModal"')
        self.assertContains(response, reverse("accounts:profile_delete"))


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


class FakeRecaptchaResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def recaptcha_success():
    return FakeRecaptchaResponse({"success": True})


@override_settings(RECAPTCHA_SITE_KEY="test-site", RECAPTCHA_SECRET_KEY="test-secret")
class RecaptchaHelperTest(TestCase):
    def test_valid_token_returns_true(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            return_value=recaptcha_success(),
        ):
            self.assertTrue(verify_recaptcha_token("token"))

    def test_unsuccessful_response_returns_false(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            return_value=FakeRecaptchaResponse({"success": False}),
        ):
            self.assertFalse(verify_recaptcha_token("token"))

    def test_network_error_returns_false(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            side_effect=Exception("timeout"),
        ):
            self.assertFalse(verify_recaptcha_token("token"))

    def test_empty_token_returns_false(self):
        self.assertFalse(verify_recaptcha_token(""))

    @override_settings(RECAPTCHA_SITE_KEY="", RECAPTCHA_SECRET_KEY="")
    def test_unconfigured_keys_skip_verification(self):
        self.assertTrue(verify_recaptcha_token(""))


@override_settings(RECAPTCHA_SITE_KEY="test-site", RECAPTCHA_SECRET_KEY="test-secret")
class RecaptchaFormsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cliente@example.com",
            password="senha-forte-123",
            name="Cliente Teste",
            is_active=True,
            email_verified_at=timezone.now(),
        )
        mail.outbox.clear()

    def test_login_blocked_without_valid_token(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            return_value=FakeRecaptchaResponse({"success": False}),
        ):
            response = self.client.post(
                reverse("accounts:login"),
                {"email": self.user.email, "password": "senha-forte-123"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verificação de segurança falhou")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_allowed_with_valid_token(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            return_value=recaptcha_success(),
        ):
            response = self.client.post(
                reverse("accounts:login"),
                {
                    "email": self.user.email,
                    "password": "senha-forte-123",
                    "g-recaptcha-response": "token",
                },
            )
        self.assertRedirects(response, reverse("website:home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_blocked_without_valid_token(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            return_value=FakeRecaptchaResponse({"success": False}),
        ):
            response = self.client.post(
                reverse("accounts:register"),
                {
                    "name": "Bot",
                    "email": "bot@example.com",
                    "phone": "",
                    "password1": "senha-forte-123",
                    "password2": "senha-forte-123",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verificação de segurança falhou")
        self.assertFalse(User.objects.filter(email="bot@example.com").exists())

    def test_password_reset_blocked_without_valid_token(self):
        with patch(
            "apps.accounts.recaptcha.requests.post",
            return_value=FakeRecaptchaResponse({"success": False}),
        ):
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": self.user.email},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verificação de segurança falhou")
        time.sleep(0.1)
        self.assertEqual(len(mail.outbox), 0)


class RecaptchaNoticeTest(TestCase):
    def test_widget_rendered_on_auth_pages(self):
        for url_name in (
            "accounts:login",
            "accounts:register",
            "accounts:password_reset",
        ):
            response = self.client.get(reverse(url_name))
            self.assertContains(response, 'class="g-recaptcha"')
            self.assertContains(
                response, "https://www.google.com/recaptcha/api.js"
            )
