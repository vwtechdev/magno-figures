from decimal import Decimal
from io import BytesIO
import json
import re

from PIL import Image
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.categories.models import Category
from apps.figures.models import Figure
from apps.website.models import Website


def make_image(name="figure.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class CatalogPaginationTest(TestCase):
    def setUp(self):
        cache.clear()
        for index in range(1, 14):
            Figure.objects.create(
                name=f"Figure {index}",
                slug=f"figure-{index}",
                description=f"Action figure número {index}.",
                price=Decimal("39.90"),
                stock=3,
                image=make_image(),
            )
        Figure.objects.create(
            name="Figure Inativa",
            slug="figure-inativa",
            description="Não deve aparecer no catálogo.",
            price=Decimal("10.00"),
            stock=0,
            image=make_image(),
            is_active=False,
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

    def test_list_returns_12_per_page(self):
        response = self.client.get(reverse("figures:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 13)
        self.assertEqual(len(response.context["figures"]), 12)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())

        response = self.client.get(reverse("figures:list"), {"page": 2})
        self.assertEqual(len(response.context["figures"]), 1)
        self.assertFalse(response.context["page_obj"].has_next())

    def test_invalid_or_out_of_range_page_falls_back(self):
        response = self.client.get(reverse("figures:list"), {"page": "abc"})
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(len(response.context["figures"]), 12)

        response = self.client.get(reverse("figures:list"), {"page": 99})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["figures"]), 1)

    def test_search_preserves_query_in_pagination(self):
        response = self.client.get(reverse("figures:list"), {"q": "Figure"})
        self.assertEqual(len(response.context["figures"]), 12)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertEqual(response.context["page_query"], "q=Figure")

        response = self.client.get(
            reverse("figures:list"), {"q": "Figure", "page": 2}
        )
        self.assertEqual(len(response.context["figures"]), 1)
        self.assertEqual(response.context["page_query"], "q=Figure")

        response = self.client.get(reverse("figures:list"))
        self.assertEqual(response.context["page_query"], "")


class FigureDetailSeoTest(TestCase):
    def setUp(self):
        cache.clear()
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            description="Catálogo de action figures.",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.category = Category.objects.create(name="Marvel", slug="marvel")
        self.figure = Figure.objects.create(
            name="Iron Man",
            slug="iron-man",
            description="Action figure do Homem de Ferro.",
            price=Decimal("199.90"),
            stock=3,
            image=make_image("iron.png"),
        )
        self.figure.categories.add(self.category)

    def test_detail_og_product_and_structured_data(self):
        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertContains(response, '<meta property="og:type" content="product">')
        self.assertContains(
            response,
            f'<meta property="og:image" content="{settings.BASE_URL}{self.figure.first_image.url}">',
        )
        html = response.content.decode()
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S
        )
        for block in blocks:
            json.loads(block)
        self.assertContains(response, '"@type": "Product"')
        self.assertContains(response, '"price": "199.90"')
        self.assertContains(response, '"priceCurrency": "BRL"')
        self.assertContains(response, "https://schema.org/InStock")
        self.assertContains(response, '"@type": "BreadcrumbList"')
        self.assertContains(response, '"name": "Iron Man"')

    def test_detail_og_image_out_of_stock(self):
        self.figure.stock = 0
        self.figure.save()
        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertContains(response, "https://schema.org/OutOfStock")