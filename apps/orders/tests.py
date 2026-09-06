from decimal import Decimal
from io import BytesIO
import time
from unittest import mock

from PIL import Image
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.addresses.models import Address
from apps.figures.models import Figure
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.website.models import Website


def make_image(name="figure.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(SUPERFRETE_TOKEN="", DEBUG=True)
class CheckoutFlowTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="cliente@example.com",
            password="senha-forte-123",
            name="Cliente Teste",
            phone="(11) 99999-0000",
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
        self.figure = Figure.objects.create(
            name="Figure Teste",
            slug="figure-teste",
            description="Action figure de teste.",
            price=Decimal("99.90"),
            stock=5,
            image=make_image(),
        )
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="(11) 99999-9999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.client.force_login(self.user)

    def _add_to_cart(self, quantity=1):
        self.user.cart.items.create(figure=self.figure, quantity=quantity)

    def test_checkout_creates_order_items_and_clears_cart(self):
        self._add_to_cart(quantity=2)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "PAC",
                "cpf": "12345678909",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.startswith(
                "https://api.whatsapp.com/send?phone=5511999999999&text="
            )
        )
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertEqual(order.address, self.address)
        self.assertEqual(order.shipping_service, "PAC")
        self.assertEqual(order.shipping_price, Decimal("59.80"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.cpf, "12345678909")
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.figure, self.figure)
        self.assertEqual(item.price, Decimal("99.90"))
        self.assertEqual(item.quantity, 2)
        self.assertEqual(order.total, Decimal("199.80"))
        self.assertFalse(self.user.cart.items.exists())
        message = order.generate_whatsapp_message()
        self.assertIn("*CPF:* 12345678909", message)
        self.assertIn("*Frete:* R$ 59.80 (PAC)", message)
        self.assertIn("*Total:* R$ 259.60", message)
        self.assertIn("Tenho interesse em finalizar este pedido!", message)
        self.assertNotIn("Gostaria de finalizar", message)
        self.assertIn(f"/orders/{order.pk}/", message)

        detail = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertContains(detail, "Frete")
        self.assertContains(detail, "R$ 59,80 (PAC)")
        self.assertContains(detail, "R$ 259,60")

    def test_checkout_uses_existing_cpf_without_asking(self):
        self.user.cpf = "11122233344"
        self.user.save(update_fields=["cpf"])
        self._add_to_cart(quantity=1)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "SEDEX",
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.shipping_service, "SEDEX")
        self.assertEqual(self.user.cpf, "11122233344")

    def test_checkout_requires_cpf(self):
        self._add_to_cart(quantity=1)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "PAC",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_checkout_rejects_invalid_cpf(self):
        self._add_to_cart(quantity=1)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "PAC",
                "cpf": "12345678900",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_checkout_blocked_with_sold_out_item(self):
        self._add_to_cart(quantity=1)
        self.figure.sold_out = True
        self.figure.save()

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "PAC",
                "cpf": "12345678909",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "esgotado")
        self.assertFalse(Order.objects.exists())
        self.assertTrue(self.user.cart.items.exists())

    def test_checkout_shipping_endpoint_aggregates_cart(self):
        self._add_to_cart(quantity=2)

        response = self.client.get(
            reverse("orders:checkout_shipping"), {"zipcode": "01310-100"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data["options"],
            [
                {"name": "PAC", "price": 59.80, "delivery_time": 7},
                {"name": "SEDEX", "price": 99.80, "delivery_time": 3},
            ],
        )

    def test_checkout_freezes_figure_price(self):
        self._add_to_cart(quantity=1)

        self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "PAC",
                "cpf": "12345678909",
            },
        )

        self.figure.price = Decimal("150.00")
        self.figure.save()
        item = OrderItem.objects.get(order__user=self.user)
        self.assertEqual(item.price, Decimal("99.90"))

    def test_checkout_empty_cart_redirects_to_cart(self):
        response = self.client.post(
            reverse("orders:checkout"), {"address_id": self.address.pk}
        )

        self.assertRedirects(response, reverse("carts:detail"))
        self.assertFalse(Order.objects.exists())

@override_settings(SUPERFRETE_TOKEN="", DEBUG=True)
class CheckoutDiscountTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="promo@example.com",
            password="senha-forte-123",
            name="Cliente Promo",
            phone="(11) 99999-0000",
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
        self.figure = Figure.objects.create(
            name="Figure Promo",
            slug="figure-promo",
            description="Com desconto.",
            price=Decimal("100.00"),
            discount_percent=10,
            stock=5,
            image=make_image(),
        )
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="(11) 99999-9999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.client.force_login(self.user)

    def test_checkout_freezes_sale_price(self):
        self.user.cart.items.create(figure=self.figure, quantity=2)
        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": "PAC",
                "cpf": "12345678909",
            },
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        item = order.items.get()
        self.assertEqual(item.price, Decimal("90.00"))
        self.assertEqual(order.total, Decimal("180.00"))


@override_settings(SUPERFRETE_TOKEN="", DEBUG=True)
class CheckoutShippingFailureTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="semfrete@example.com",
            password="senha-forte-123",
            name="Cliente Sem Frete",
            phone="(11) 99999-0000",
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
        self.figure = Figure.objects.create(
            name="Figure Sem Frete",
            slug="figure-sem-frete",
            description="Teste de falha de frete.",
            price=Decimal("100.00"),
            stock=5,
            image=make_image(),
        )
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="(11) 99999-9999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.client.force_login(self.user)
        self.user.cart.items.create(figure=self.figure, quantity=1)

    def _post(self, service):
        return self.client.post(
            reverse("orders:checkout"),
            {
                "address_id": self.address.pk,
                "shipping_service": service,
                "cpf": "12345678909",
            },
        )

    def test_combine_allowed_when_api_fails(self):
        with mock.patch(
            "apps.orders.views.cart_shipping_options",
            return_value=([], "Não foi possível consultar o frete agora."),
        ):
            response = self._post("combine")
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.shipping_service, "A combinar")
        self.assertIsNone(order.shipping_price)
        message = order.generate_whatsapp_message()
        self.assertNotIn("*Frete:*", message)
        self.assertIn("*Total:* R$ 100.00", message)
        detail = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertContains(detail, "A combinar")

    def test_other_value_blocked_when_api_fails(self):
        with mock.patch(
            "apps.orders.views.cart_shipping_options",
            return_value=([], "Não foi possível consultar o frete agora."),
        ):
            response = self._post("PAC")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_combine_rejected_when_api_works(self):
        response = self._post("combine")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(user=self.user).exists())


class CheckoutCpfStepTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="cpfstep@example.com",
            password="senha-forte-123",
            name="Cliente CPF",
            phone="(11) 99999-0000",
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
        self.figure = Figure.objects.create(
            name="Figure CPF",
            slug="figure-cpf",
            description="Teste de etapa CPF.",
            price=Decimal("50.00"),
            stock=5,
            image=make_image(),
        )
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="(11) 99999-9999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.client.force_login(self.user)
        self.user.cart.items.create(figure=self.figure, quantity=1)

    def test_cpf_step_rendered_without_cpf(self):
        response = self.client.get(reverse("orders:checkout"))
        self.assertContains(response, 'data-step="cpf"')
        self.assertContains(response, "Etapa 1 de 4")

    def test_cpf_step_skipped_with_cpf(self):
        self.user.cpf = "12345678909"
        self.user.save(update_fields=["cpf"])
        response = self.client.get(reverse("orders:checkout"))
        self.assertNotContains(response, 'data-step="cpf"')
        self.assertContains(response, "Etapa 1 de 3")
        self.assertContains(response, "3. Resumo do pedido")


class OrderTrackingTest(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.user = User.objects.create_user(
            email="rastreio@example.com",
            password="senha-forte-123",
            name="Cliente Rastreio",
            phone="(11) 99999-0000",
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
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="(11) 99999-9999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.client.force_login(self.user)

    def _make_order(self, **kwargs):
        defaults = {"user": self.user, "address": self.address}
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def _wait_for_email(self, timeout=2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if mail.outbox:
                return True
            time.sleep(0.01)
        return False

    def test_sent_without_code_rejected(self):
        order = self._make_order(status=OrderStatus.SENT)
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_sent_with_code_accepted(self):
        order = self._make_order(
            status=OrderStatus.SENT, tracking_code="BR123456789BR"
        )
        order.full_clean()

    def test_new_without_code_accepted(self):
        order = self._make_order(status=OrderStatus.NEW)
        order.full_clean()

    def test_transition_to_sent_sends_email(self):
        order = self._make_order(
            shipping_service="PAC", tracking_code="BR123456789BR"
        )
        order.status = OrderStatus.SENT
        order.save()
        self.assertTrue(self._wait_for_email(), "e-mail não foi enviado a tempo")
        message = mail.outbox[0]
        self.assertEqual(message.to, ["rastreio@example.com"])
        self.assertIn("BR123456789BR", message.body)
        self.assertIn("https://rastreamento.correios.com.br/", message.body)

    def test_edit_without_status_change_sends_nothing(self):
        order = self._make_order(
            status=OrderStatus.SENT, tracking_code="BR123456789BR"
        )
        mail.outbox.clear()
        order.tracking_code = "BR987654321BR"
        order.save()
        time.sleep(0.3)
        self.assertEqual(len(mail.outbox), 0)

    def test_tracking_url_always_correios(self):
        order = self._make_order(tracking_code="ABC123")
        for service in ("SEDEX", "Mini Envios", "Jadlog", "Loggi", "A combinar", ""):
            order.shipping_service = service
            self.assertEqual(
                order.tracking_url, "https://rastreamento.correios.com.br/"
            )
        order.tracking_code = ""
        order.shipping_service = "PAC"
        self.assertIsNone(order.tracking_url)

    def test_detail_shows_tracking_block(self):
        order = self._make_order(
            status=OrderStatus.SENT,
            shipping_service="PAC",
            tracking_code="BR123456789BR",
        )
        response = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertContains(response, "BR123456789BR")
        self.assertContains(response, "Rastrear pedido")
        self.assertContains(response, 'id="copyTracking"')
        self.assertContains(
            response, "https://rastreamento.correios.com.br/"
        )

    def test_detail_hides_tracking_without_code(self):
        order = self._make_order(status=OrderStatus.PAID)
        response = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertNotContains(response, "Rastrear pedido")


class OrderAdminActionsTest(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="senha-forte-123",
            name="Admin",
        )
        self.user = User.objects.create_user(
            email="acao@example.com",
            password="senha-forte-123",
            name="Cliente Ação",
            phone="(11) 99999-0000",
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
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.order = Order.objects.create(
            user=self.user,
            address=self.address,
            status=OrderStatus.NEW,
        )
        self.client.force_login(self.admin)

    def _post(self, name):
        return self.client.post(
            reverse(name, args=[self.order.pk])
        )

    def test_confirmation_sets_status_and_opens_whatsapp(self):
        response = self._post("admin:orders_order_send_confirmation")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CONFIRM)
        self.assertEqual(response.status_code, 200)
        url = response.json()["url"]
        self.assertTrue(
            url.startswith("https://api.whatsapp.com/send?phone=")
        )
        self.assertIn("Confirma%20a%20realiza", url)

    def test_production_sets_status_and_opens_whatsapp(self):
        response = self._post("admin:orders_order_send_production")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PRODUCTION)
        self.assertEqual(response.status_code, 200)
        self.assertIn("produ", response.json()["url"])

    def test_shipment_with_code_sets_status_and_opens_whatsapp(self):
        self.order.tracking_code = "BR123456789BR"
        self.order.save()
        response = self._post("admin:orders_order_send_shipment")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.SENT)
        self.assertEqual(response.status_code, 200)
        self.assertIn("BR123456789BR", response.json()["url"])

    def test_shipment_without_code_stays(self):
        response = self._post("admin:orders_order_send_shipment")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_get_does_not_change_status(self):
        response = self.client.get(
            reverse("admin:orders_order_send_confirmation", args=[self.order.pk])
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)
        self.assertEqual(response.status_code, 405)

    def test_requires_staff(self):
        self.client.logout()
        response = self.client.post(
            reverse("admin:orders_order_send_confirmation", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.NEW)

    def test_message_contents(self):
        self.assertIn("entrou em *produção*", self.order.generate_production_message())
        shipment = Order.objects.create(
            user=self.user,
            address=self.address,
            status=OrderStatus.SENT,
            shipping_service="PAC",
            tracking_code="BR123456789BR",
        )
        message = shipment.generate_shipment_message()
        self.assertIn("foi *enviado*", message)
        self.assertIn("BR123456789BR", message)
        self.assertIn("https://rastreamento.correios.com.br/", message)

    def test_change_form_renders_jazzmin_buttons(self):
        response = self.client.get(
            reverse("admin:orders_order_change", args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                "admin:orders_order_send_confirmation", args=[self.order.pk]
            ),
        )
        self.assertContains(
            response,
            reverse(
                "admin:orders_order_send_production", args=[self.order.pk]
            ),
        )
        self.assertContains(
            response,
            reverse("admin:orders_order_send_shipment", args=[self.order.pk]),
        )
        self.assertContains(response, "btn btn-success")
        self.assertContains(response, "btn btn-warning")
        self.assertContains(response, "btn btn-info")


class OrderTotalTest(TestCase):
    def test_total_is_quantized_decimal(self):
        user = User.objects.create_user(
            email="total@example.com",
            password="senha-forte-123",
            name="Cliente Total",
        )
        address = Address.objects.create(
            user=user,
            zip_code="01310-100",
            street="Av. Paulista",
            number="1000",
            neighborhood="Bela Vista",
            city="São Paulo",
            state="SP",
        )
        figure = Figure.objects.create(
            name="Figure Total",
            slug="figure-total",
            description="Teste de total.",
            price=Decimal("799.90"),
            stock=5,
            image=make_image(),
        )
        order = Order.objects.create(user=user, address=address)
        OrderItem.objects.create(
            order=order, figure=figure, quantity=1, price=figure.price
        )
        self.assertEqual(order.total, Decimal("799.90"))
        self.assertIsInstance(order.total, Decimal)
