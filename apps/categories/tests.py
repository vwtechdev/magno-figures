import json
import re
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.categories.gating import AGE_VERIFIED_SESSION_KEY
from apps.categories.models import Category
from apps.figures.models import Figure
from apps.website.models import Website
from core.utils import site_base_url


def make_image(name="category.png"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class CategoryBreadcrumbSeoTest(TestCase):
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
        self.avo = Category.objects.create(name="Avô", slug="avo")
        self.pai = Category.objects.create(name="Pai", slug="pai", parent=self.avo)
        self.filha = Category.objects.create(name="Filha", slug="filha", parent=self.pai)

    def test_breadcrumb_structured_data_with_ancestors(self):
        response = self.client.get(
            reverse("categories:detail", args=[self.filha.slug])
        )
        html = response.content.decode()
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S
        )
        for block in blocks:
            json.loads(block)
        self.assertContains(response, '"@type": "BreadcrumbList"')
        self.assertContains(response, '"name": "Avô"')
        self.assertContains(response, '"name": "Pai"')
        self.assertContains(response, '"name": "Filha"')
        self.assertContains(response, f'"{site_base_url()}/categories/filha/"')


class NsfwAgeGateTest(TestCase):
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
        self.safe_cat = Category.objects.create(name="Marvel", slug="marvel")
        self.nsfw_cat = Category.objects.create(
            name="+18", slug="mais-18", is_nsfw=True
        )
        self.child_cat = Category.objects.create(
            name="Sub +18", slug="sub-18", parent=self.nsfw_cat
        )
        self.safe_figure = Figure.objects.create(
            name="Iron Man",
            slug="iron-man",
            description="Herói.",
            price=Decimal("199.90"),
            stock=3,
            image=make_image("iron.png"),
        )
        self.safe_figure.categories.add(self.safe_cat)
        self.nsfw_figure = Figure.objects.create(
            name="Dark Lady",
            slug="dark-lady",
            description="Conteúdo adulto.",
            price=Decimal("299.90"),
            stock=3,
            image=make_image("dark.png"),
        )
        self.nsfw_figure.categories.add(self.nsfw_cat)
        self.child_figure = Figure.objects.create(
            name="Shadow",
            slug="shadow",
            description="Conteúdo adulto indireto.",
            price=Decimal("99.90"),
            stock=3,
            image=make_image("shadow.png"),
        )
        self.child_figure.categories.add(self.child_cat)

    def _gate_url(self, path):
        return f"{reverse('categories:age_gate')}?{urlencode({'next': path})}"

    def _verify_age(self, next_url="/"):
        return self.client.post(
            reverse("categories:age_gate"),
            {"confirm": "yes", "next": next_url},
        )

    def test_nsfw_inheritance(self):
        self.assertFalse(self.safe_cat.is_nsfw_effective)
        self.assertTrue(self.nsfw_cat.is_nsfw_effective)
        self.assertTrue(self.child_cat.is_nsfw_effective)
        self.assertFalse(self.safe_figure.is_nsfw)
        self.assertTrue(self.nsfw_figure.is_nsfw)
        self.assertTrue(self.child_figure.is_nsfw)

    def test_unverified_catalog_home_and_search_hide_nsfw(self):
        for url in (reverse("figures:list"), reverse("website:home")):
            response = self.client.get(url)
            self.assertContains(response, "Iron Man")
            self.assertNotContains(response, "Dark Lady")
            self.assertNotContains(response, "Shadow")
        response = self.client.get(reverse("figures:list"), {"q": "Conteúdo"})
        self.assertNotContains(response, "Dark Lady")
        self.assertNotContains(response, "Shadow")

    def test_nsfw_category_hidden_until_verified(self):
        response = self.client.get(reverse("categories:list"))
        self.assertContains(response, "Marvel")
        self.assertNotContains(response, "mais-18")
        self.assertNotContains(response, "+18")

    def test_nsfw_filter_always_in_catalog_sidebar(self):
        response = self.client.get(reverse("figures:list"))
        sidebar = list(response.context["filter_categories"])
        self.assertIn(self.safe_cat, sidebar)
        self.assertIn(self.nsfw_cat, sidebar)
        self.assertIn(self.child_cat, sidebar)

    def test_nsfw_category_listed_once_verified(self):
        self._verify_age(reverse("categories:list"))
        response = self.client.get(reverse("categories:list"))
        self.assertContains(response, "mais-18")
        self.assertContains(response, "+18")
        response = self.client.get(reverse("figures:list"))
        sidebar = list(response.context["filter_categories"])
        self.assertIn(self.safe_cat, sidebar)
        self.assertIn(self.nsfw_cat, sidebar)
        self.assertIn(self.child_cat, sidebar)

    def test_empty_category_hidden_from_catalog_sidebar(self):
        Category.objects.create(name="Vazia", slug="vazia")
        parent = Category.objects.create(name="Pai Vazio", slug="pai-vazio")
        child = Category.objects.create(
            name="Filha Cheia", slug="filha-cheia", parent=parent
        )
        self.safe_figure.categories.add(child)
        response = self.client.get(reverse("figures:list"))
        slugs = [c.slug for c in response.context["filter_categories"]]
        self.assertNotIn("vazia", slugs)
        self.assertNotContains(response, "Vazia")
        self.assertIn("pai-vazio", slugs)
        self.assertIn("filha-cheia", slugs)

    def test_nsfw_category_hidden_from_navbar(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, "Catálogo")
        self.assertNotContains(response, "Marvel")
        self.assertNotContains(response, "mais-18")
        self.assertNotContains(response, "+18")

    def test_nsfw_detail_redirects_to_gate(self):
        path = reverse("figures:detail", args=[self.nsfw_figure.slug])
        response = self.client.get(path)
        self.assertRedirects(response, self._gate_url(path))
        path = reverse("categories:detail", args=[self.nsfw_cat.slug])
        response = self.client.get(path)
        self.assertRedirects(response, self._gate_url(path))

    def test_gate_page_is_noindex(self):
        response = self.client.get(reverse("categories:age_gate"))
        self.assertContains(
            response, '<meta name="robots" content="noindex, nofollow">'
        )

    def test_gate_decline_redirects_home(self):
        response = self.client.post(
            reverse("categories:age_gate"), {"next": "/"}
        )
        self.assertRedirects(response, "/")
        self.assertNotIn(AGE_VERIFIED_SESSION_KEY, self.client.session)

    def test_gate_flow_grants_access(self):
        path = reverse("figures:detail", args=[self.nsfw_figure.slug])
        response = self._verify_age(path)
        self.assertRedirects(response, path)
        self.assertTrue(self.client.session.get(AGE_VERIFIED_SESSION_KEY))
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, '<meta name="robots" content="noindex, nofollow">'
        )
        self.assertContains(response, "+18")
        response = self.client.get(reverse("figures:list"))
        self.assertNotContains(response, "Dark Lady")
        response = self.client.get(
            reverse("figures:list"), {"cat": "mais-18"}
        )
        self.assertContains(response, "Dark Lady")

    def test_verified_without_nsfw_filter_hides_nsfw_on_home(self):
        self._verify_age("/")
        response = self.client.get(reverse("website:home"))
        self.assertNotContains(response, "Dark Lady")
        self.assertNotContains(response, "Shadow")
        self.assertContains(response, "Iron Man")

    def test_safe_pages_keep_index_follow(self):
        path = reverse("figures:detail", args=[self.safe_figure.slug])
        response = self.client.get(path)
        self.assertContains(
            response, '<meta name="robots" content="index, follow">'
        )

    def test_nsfw_excluded_from_sitemap(self):
        response = self.client.get("/sitemap.xml")
        content = response.content.decode()
        self.assertIn("/figures/iron-man/", content)
        self.assertIn("/categories/marvel/", content)
        self.assertNotIn("/figures/dark-lady/", content)
        self.assertNotIn("/figures/shadow/", content)
        self.assertNotIn("/categories/mais-18/", content)
        self.assertNotIn("/categories/sub-18/", content)

    def test_add_to_cart_blocked_until_verified(self):
        add_url = reverse("carts:add", args=[self.nsfw_figure.pk])
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("categories:age_gate")))
        self.assertEqual(self.client.session.get("cart") or {}, {})
        self._verify_age("/")
        response = self.client.get(add_url)
        self.assertEqual(self.client.session.get("cart"), {str(self.nsfw_figure.pk): 1})