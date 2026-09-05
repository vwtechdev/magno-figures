from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.figures.models import Figure


def make_image(name="figure.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class CartLogicTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="cliente@example.com",
            password="senha-forte-123",
            name="Cliente Teste",
        )
        self.figure = Figure.objects.create(
            name="Figure Teste",
            slug="figure-teste",
            description="Action figure de teste.",
            price=Decimal("49.90"),
            stock=5,
            image=make_image(),
        )
        self.client.force_login(self.user)

    def test_add_existing_figure_increments_quantity(self):
        self.client.get(reverse("carts:add", args=[self.figure.pk]))
        self.client.get(reverse("carts:add", args=[self.figure.pk]))

        self.assertEqual(self.user.cart.items.count(), 1)
        self.assertEqual(self.user.cart.items.get().quantity, 2)

    def test_add_respects_stock_cap(self):
        self.figure.stock = 1
        self.figure.save()

        self.client.get(reverse("carts:add", args=[self.figure.pk]))
        self.client.get(reverse("carts:add", args=[self.figure.pk]))

        self.assertEqual(self.user.cart.items.get().quantity, 1)

    def test_update_dec_deletes_when_quantity_one(self):
        self.user.cart.items.create(figure=self.figure, quantity=2)

        self.client.post(
            reverse("carts:update", args=[self.figure.pk]), {"action": "dec"}
        )
        self.assertEqual(self.user.cart.items.get().quantity, 1)

        self.client.post(
            reverse("carts:update", args=[self.figure.pk]), {"action": "dec"}
        )
        self.assertFalse(self.user.cart.items.exists())

    def test_remove_deletes_item(self):
        self.user.cart.items.create(figure=self.figure, quantity=3)

        self.client.get(reverse("carts:remove", args=[self.figure.pk]))

        self.assertFalse(self.user.cart.items.exists())

    def test_add_sold_out_figure_blocked(self):
        self.figure.sold_out = True
        self.figure.save()

        self.client.get(reverse("carts:add", args=[self.figure.pk]))

        self.assertFalse(self.user.cart.items.exists())

    def test_update_inc_sold_out_keeps_quantity(self):
        self.user.cart.items.create(figure=self.figure, quantity=2)
        self.figure.sold_out = True
        self.figure.save()

        self.client.post(
            reverse("carts:update", args=[self.figure.pk]), {"action": "inc"}
        )

        self.assertEqual(self.user.cart.items.get().quantity, 2)

    def test_add_preorder_stock_zero_allowed(self):
        self.figure.stock = 0
        self.figure.save()

        self.client.get(reverse("carts:add", args=[self.figure.pk]))

        self.assertEqual(self.user.cart.items.get().quantity, 1)