from decimal import Decimal
from io import BytesIO
import json
import os
import re
import tempfile
import time
from unittest import mock

import requests
from PIL import Image
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.categories.models import Category
from apps.figures.models import Figure, FigureImage, StockAlert
from apps.figures.notifications import stock_alert_token
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


class FigureFileStorageTest(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_delete_figure_removes_image_and_gallery(self):
        figure = Figure.objects.create(
            name="Figura A", slug="figura-a", description="d",
            price=Decimal("10.00"), stock=1, image=make_image("f.png"),
        )
        gallery = FigureImage.objects.create(figure=figure, image=make_image("g.png"))
        paths = [figure.image.path, gallery.image.path]
        self.assertTrue(all(os.path.exists(path) for path in paths))

        figure.delete()

        self.assertFalse(any(os.path.exists(path) for path in paths))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_update_figure_image_removes_old_file(self):
        figure = Figure.objects.create(
            name="Figura B", slug="figura-b", description="d",
            price=Decimal("10.00"), stock=1, image=make_image("f1.png"),
        )
        old_path = figure.image.path

        figure.image = make_image("f2.png")
        figure.save()

        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(figure.image.path))


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


class CatalogFilterTest(TestCase):
    def setUp(self):
        cache.clear()
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.anime = Category.objects.create(name="Anime", slug="anime")
        self.naruto = Category.objects.create(
            name="Naruto", slug="naruto", parent=self.anime
        )
        self.marvel = Category.objects.create(name="Marvel", slug="marvel")
        self.adult = Category.objects.create(
            name="+18", slug="mais-18", is_nsfw=True
        )
        self.naruto_fig = self._make_figure("Naruto Figure", "naruto-fig", "100.00")
        self.naruto_fig.categories.add(self.naruto)
        self.goku_fig = self._make_figure("Goku Figure", "goku-fig", "200.00")
        self.goku_fig.categories.add(self.anime)
        self.iron_fig = self._make_figure("Iron Man", "iron-man", "300.00")
        self.iron_fig.categories.add(self.marvel)
        self.dark_fig = self._make_figure("Dark Lady", "dark-lady", "400.00")
        self.dark_fig.categories.add(self.adult)

    def _make_figure(self, name, slug, price):
        return Figure.objects.create(
            name=name,
            slug=slug,
            description=f"Figure {name}.",
            price=Decimal(price),
            stock=3,
            image=make_image(f"{slug}.png"),
        )

    def test_multi_select_returns_union(self):
        response = self.client.get(reverse("figures:list"), {"cat": ["anime", "marvel"]})
        self.assertContains(response, "Naruto Figure")
        self.assertContains(response, "Goku Figure")
        self.assertContains(response, "Iron Man")
        self.assertNotContains(response, "Dark Lady")

    def test_parent_includes_child_categories(self):
        response = self.client.get(reverse("figures:list"), {"cat": "anime"})
        self.assertContains(response, "Naruto Figure")
        self.assertContains(response, "Goku Figure")
        self.assertNotContains(response, "Iron Man")

    def test_invalid_category_slug_ignored(self):
        response = self.client.get(reverse("figures:list"), {"cat": "nope"})
        self.assertContains(response, "Naruto Figure")
        self.assertContains(response, "Iron Man")

    def test_min_and_max_price(self):
        response = self.client.get(reverse("figures:list"), {"min_price": "150"})
        self.assertNotContains(response, "Naruto Figure")
        self.assertContains(response, "Goku Figure")
        self.assertContains(response, "Iron Man")
        response = self.client.get(reverse("figures:list"), {"max_price": "150"})
        self.assertContains(response, "Naruto Figure")
        self.assertNotContains(response, "Goku Figure")

    def test_price_accepts_comma_and_swaps_inverted_range(self):
        response = self.client.get(
            reverse("figures:list"),
            {"min_price": "150,00", "max_price": "250,00"},
        )
        self.assertNotContains(response, "Naruto Figure")
        self.assertContains(response, "Goku Figure")
        self.assertNotContains(response, "Iron Man")
        response = self.client.get(
            reverse("figures:list"),
            {"min_price": "300", "max_price": "100"},
        )
        self.assertContains(response, "Naruto Figure")
        self.assertContains(response, "Goku Figure")
        self.assertContains(response, "Iron Man")

    def test_invalid_price_ignored(self):
        response = self.client.get(reverse("figures:list"), {"min_price": "abc"})
        self.assertContains(response, "Naruto Figure")
        self.assertContains(response, "Iron Man")

    def test_filters_combine_with_search(self):
        response = self.client.get(
            reverse("figures:list"), {"q": "Naruto", "cat": "marvel"}
        )
        self.assertContains(response, "Nenhum resultado encontrado.")

    def test_pagination_preserves_filter_params(self):
        response = self.client.get(
            reverse("figures:list"), {"cat": "anime", "min_price": "50"}
        )
        page_query = response.context["page_query"]
        self.assertIn("cat=anime", page_query)
        self.assertIn("min_price=50", page_query)

    def test_ajax_returns_json_with_html(self):
        response = self.client.get(
            reverse("figures:list"),
            {"cat": "marvel"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertIn("Iron Man", payload["html"])
        self.assertNotIn("Naruto Figure", payload["html"])

    def test_verified_selection_shows_nsfw_figures(self):
        self.client.post(
            reverse("categories:age_gate"), {"confirm": "yes", "next": "/"}
        )
        response = self.client.get(reverse("figures:list"), {"cat": "mais-18"})
        self.assertContains(response, "Dark Lady")
        self.assertNotContains(response, "Confirmar idade")

    def test_sidebar_shows_nsfw_category_with_gate_invitation(self):
        response = self.client.get(reverse("figures:list"))
        slugs = [c.slug for c in response.context["filter_categories"]]
        self.assertIn("anime", slugs)
        self.assertIn("mais-18", slugs)
        self.assertContains(response, "+18")
        response = self.client.get(reverse("figures:list"), {"cat": "mais-18"})
        self.assertContains(
            response, "Esta categoria contém conteúdo para maiores de 18 anos."
        )
        self.assertContains(response, reverse("categories:age_gate"))

class StockAlertTest(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        self.figure = Figure.objects.create(
            name="Iron Man",
            slug="iron-man",
            description="Action figure do Homem de Ferro.",
            price=Decimal("199.90"),
            stock=0,
            sold_out=True,
            image=make_image("iron.png"),
        )

    def _wait_for_email(self, timeout=2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if mail.outbox:
                return True
            time.sleep(0.01)
        return False

    def test_sold_out_page_shows_notify_form(self):
        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertContains(response, "Me avise quando disponível")
        self.assertContains(
            response, reverse("figures:notify", args=[self.figure.slug])
        )

    def test_available_page_has_no_notify_form(self):
        self.figure.sold_out = False
        self.figure.save()
        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertNotContains(response, "Me avise quando disponível")

    def test_subscribe_creates_alert(self):
        response = self.client.post(
            reverse("figures:notify", args=[self.figure.slug]),
            {"email": "cliente@example.com"},
            follow=True,
        )
        self.assertTrue(
            StockAlert.objects.filter(
                figure=self.figure, email="cliente@example.com"
            ).exists()
        )
        self.assertContains(response, "Avisaremos quando estiver disponível.")

    def test_subscribe_duplicate_keeps_single_alert(self):
        url = reverse("figures:notify", args=[self.figure.slug])
        self.client.post(url, {"email": "cliente@example.com"})
        response = self.client.post(
            url, {"email": "cliente@example.com"}, follow=True
        )
        self.assertEqual(
            StockAlert.objects.filter(figure=self.figure).count(), 1
        )
        self.assertContains(response, "já está na lista de avisos.")

    def test_subscribe_invalid_email_rejected(self):
        response = self.client.post(
            reverse("figures:notify", args=[self.figure.slug]),
            {"email": "nao-email"},
            follow=True,
        )
        self.assertEqual(
            StockAlert.objects.filter(figure=self.figure).count(), 0
        )
        self.assertContains(response, "Informe um email válido.")

    def test_subscribe_available_figure_rejected(self):
        self.figure.sold_out = False
        self.figure.save()
        response = self.client.post(
            reverse("figures:notify", args=[self.figure.slug]),
            {"email": "cliente@example.com"},
            follow=True,
        )
        self.assertEqual(
            StockAlert.objects.filter(figure=self.figure).count(), 0
        )
        self.assertContains(response, "já está disponível.")

    def test_restock_sends_email_and_marks_notified(self):
        alert = StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        self.figure.sold_out = False
        self.figure.save()
        self.assertTrue(self._wait_for_email(), "e-mail não foi enviado a tempo")
        message = mail.outbox[0]
        self.assertEqual(message.to, ["cliente@example.com"])
        self.assertIn("Iron Man", message.subject)
        self.assertIn("/figures/iron-man/", message.body)
        self.assertIn("/figures/stock-alerts/unsubscribe/", message.body)
        alert.refresh_from_db()
        self.assertTrue(alert.is_notified)

    def test_other_edits_do_not_send(self):
        StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        self.figure.price = Decimal("179.90")
        self.figure.save()
        time.sleep(0.3)
        self.assertEqual(len(mail.outbox), 0)

    def test_unsubscribe_valid_token(self):
        alert = StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        token = stock_alert_token(alert)
        response = self.client.get(
            reverse("figures:unsubscribe", args=[token])
        )
        self.assertContains(response, "Aviso cancelado")
        self.assertFalse(
            StockAlert.objects.filter(pk=alert.pk).exists()
        )

    def test_unsubscribe_invalid_token(self):
        response = self.client.get(
            reverse("figures:unsubscribe", args=["invalido"])
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Link inválido", status_code=400
        )
