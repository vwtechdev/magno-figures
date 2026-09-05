from decimal import Decimal
from io import BytesIO
import json
import re
from unittest import mock

import requests
from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.categories.models import Category
from apps.figures.models import Figure
from apps.figures.services import calculate_shipping
from apps.website.models import Website
from core.utils import site_base_url


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
            f'<meta property="og:image" content="{site_base_url()}{self.figure.first_image.url}">',
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

    def test_detail_sold_out_shows_esgotado(self):
        self.figure.sold_out = True
        self.figure.save()

        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertContains(response, "Esgotado")
        self.assertNotContains(response, 'class="product__cta product__cta--buy"')


class SuperFreteShippingTest(TestCase):
    def setUp(self):
        cache.clear()
        self.figure = Figure.objects.create(
            name="Figure Frete",
            slug="figure-frete",
            description="Figure para testes de frete.",
            price=Decimal("49.90"),
            stock=5,
            image=make_image(),
        )

    def _fake_response(self, data):
        fake = mock.Mock()
        fake.raise_for_status = mock.Mock()
        fake.json = mock.Mock(return_value=data)
        return fake

    @override_settings(
        SUPERFRETE_TOKEN="token-teste", SUPERFRETE_SANDBOX=True
    )
    def test_normalizes_ceps_in_payload(self):
        with mock.patch(
            "apps.figures.services.requests.post",
            return_value=self._fake_response([]),
        ) as post:
            calculate_shipping(self.figure, "01310-100", "05311-900")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["from"]["postal_code"], "05311900")
        self.assertEqual(payload["to"]["postal_code"], "01310100")

    @override_settings(
        SUPERFRETE_TOKEN="token-teste",
        SUPERFRETE_SANDBOX=True,
        SUPERFRETE_SERVICES="1,2,17",
    )
    def test_payload_includes_configured_services(self):
        with mock.patch(
            "apps.figures.services.requests.post",
            return_value=self._fake_response([]),
        ) as post:
            calculate_shipping(self.figure, "01310100", "05311900")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["services"], "1,2,17")

    @override_settings(
        SUPERFRETE_TOKEN="token-teste", SUPERFRETE_SANDBOX=True
    )
    def test_filters_correios_and_sorts_by_price(self):
        data = [
            {
                "name": "PAC",
                "company": {"name": "Correios"},
                "price": 29.90,
                "delivery_time": 7,
                "has_error": False,
            },
            {
                "name": "Jadlog",
                "company": {"name": "Jadlog"},
                "price": 15.00,
                "delivery_time": 4,
                "has_error": False,
            },
            {
                "name": "SEDEX",
                "company": {"name": "Correios"},
                "price": 49.90,
                "delivery_time": 3,
                "has_error": False,
            },
            {
                "name": "PAC com erro",
                "company": {"name": "Correios"},
                "price": 1.00,
                "delivery_time": 9,
                "has_error": True,
            },
        ]
        with mock.patch(
            "apps.figures.services.requests.post",
            return_value=self._fake_response(data),
        ):
            options, error = calculate_shipping(self.figure, "01310100", "05311900")
        self.assertIsNone(error)
        self.assertEqual([option["name"] for option in options], ["PAC", "SEDEX"])

    @override_settings(
        SUPERFRETE_TOKEN="token-teste", SUPERFRETE_SANDBOX=True
    )
    def test_api_error_returns_friendly_message(self):
        with mock.patch(
            "apps.figures.services.requests.post",
            side_effect=requests.RequestException("boom"),
        ):
            options, error = calculate_shipping(self.figure, "01310100", "05311900")
        self.assertEqual(options, [])
        self.assertIn("Não foi possível consultar o frete", error)

    @override_settings(SUPERFRETE_TOKEN="", DEBUG=True)
    def test_no_token_in_debug_returns_mock(self):
        options, error = calculate_shipping(self.figure, "01310100", "05311900")
        self.assertIsNone(error)
        self.assertEqual(len(options), 2)

    @override_settings(SUPERFRETE_TOKEN="token-teste")
    def test_missing_origin_zip_returns_error(self):
        options, error = calculate_shipping(self.figure, "01310100", "")
        self.assertEqual(options, [])
        self.assertEqual(error, "CEP de origem não configurado.")

    @override_settings(
        SUPERFRETE_TOKEN="token-teste",
        SUPERFRETE_SANDBOX=True,
        SUPERFRETE_USER_AGENT_EMAIL="teste@exemplo.com",
    )
    def test_user_agent_uses_configurable_email(self):
        with mock.patch(
            "apps.figures.services.requests.post",
            return_value=self._fake_response([]),
        ) as post:
            calculate_shipping(self.figure, "01310100", "05311900")
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["User-Agent"], "Superfrete (teste@exemplo.com)")