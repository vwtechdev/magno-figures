from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
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
            reverse("orders:checkout"), {"address_id": self.address.pk}
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
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.figure, self.figure)
        self.assertEqual(item.price, Decimal("99.90"))
        self.assertEqual(item.quantity, 2)
        self.assertEqual(order.total, Decimal("199.80"))
        self.assertFalse(self.user.cart.items.exists())

    def test_checkout_freezes_figure_price(self):
        self._add_to_cart(quantity=1)

        self.client.post(
            reverse("orders:checkout"), {"address_id": self.address.pk}
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