import json
import os
import re
import tempfile
from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.figures.models import Figure
from apps.website.models import Banner, Website
from core.utils import site_base_url


def make_image(name="website.png"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def assert_valid_ld_json(test_case, html):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    for block in blocks:
        json.loads(block)


class WebsiteSeoTest(TestCase):
    def setUp(self):
        cache.clear()
        self.website = Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="contato@magno.com",
            description="Catálogo de action figures para colecionadores.",
            seo_keywords="action figure, colecionáveis, bonecos importados",
            google_analytics=(
                "<script async src=\"https://www.googletagmanager.com/gtag/js?id=G-XXXX\"></script>"
                "<script>window.dataLayer = window.dataLayer || [];</script>"
            ),
            twitter="https://x.com/magno_figures",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )

    def test_seo_meta_tags_rendered(self):
        response = self.client.get(reverse("website:home"))
        html = response.content.decode()
        self.assertContains(
            response,
            '<meta name="description" content="Catálogo de action figures para colecionadores.">',
        )
        self.assertContains(
            response,
            '<meta name="keywords" content="action figure, colecionáveis, bonecos importados">',
        )

    def test_google_analytics_script_rendered_unescaped(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(
            response,
            '<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script>',
        )

    def test_twitter_social_link_rendered(self):
        response = self.client.get(reverse("website:home"))
        html = response.content.decode()
        self.assertIn('<a href="https://x.com/magno_figures" target="_blank" rel="noopener"', html)
        self.assertIn('aria-label="X (Twitter)"', html)

    def test_canonical_and_open_graph_rendered(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(
            response, f'<link rel="canonical" href="{site_base_url()}/">'
        )
        self.assertContains(response, '<meta property="og:site_name" content="Magno Figures">')
        self.assertContains(response, '<meta property="og:locale" content="pt_BR">')
        self.assertContains(response, '<meta property="og:type" content="website">')
        self.assertContains(response, f'<meta property="og:url" content="{site_base_url()}/">')
        self.assertContains(
            response,
            f'<meta property="og:image" content="{site_base_url()}{self.website.logo.url}">',
        )
        self.assertContains(response, '<meta name="twitter:card" content="summary_large_image">')
        self.assertContains(response, '<meta name="robots" content="index, follow">')

    def test_structured_data_jsonld(self):
        response = self.client.get(reverse("website:home"))
        html = response.content.decode()
        assert_valid_ld_json(self, html)
        self.assertContains(response, '"@type": "WebSite"')
        self.assertContains(response, '"@type": "SearchAction"')
        self.assertContains(response, '"@type": "Organization"')
        self.assertContains(response, '"sameAs"')
        self.assertContains(response, '"https://x.com/magno_figures"')
        self.assertContains(response, '/figures/?q={search_term_string}"')

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn(
            f"Sitemap: {site_base_url()}/sitemap.xml", response.content.decode()
        )

    def test_navbar_logo_and_favicon_use_website_config(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(
            response,
            f'<img src="{self.website.logo.url}" alt="Magno Figures" class="navbar__logo">',
        )
        self.assertContains(
            response,
            f'<link rel="icon" type="image/png" href="{self.website.favicon.url}">',
        )

    def test_sitemap_xml(self):
        Figure.objects.create(
            name="Figure SEO",
            slug="figure-seo",
            description="Descrição.",
            price=Decimal("49.90"),
            stock=5,
            image=make_image("figure.png"),
        )
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        content = response.content.decode()
        self.assertIn(f"<loc>{site_base_url()}/figures/</loc>", content)
        self.assertIn(f"<loc>{site_base_url()}/about/</loc>", content)
        self.assertIn(f"<loc>{site_base_url()}/figures/figure-seo/</loc>", content)


class WebsiteEmptySeoTest(TestCase):
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

    def test_seo_meta_tags_and_analytics_omitted_when_empty(self):
        response = self.client.get(reverse("website:home"))
        html = response.content.decode()
        self.assertNotIn('<meta name="description"', html)
        self.assertNotIn('<meta name="keywords"', html)
        self.assertNotIn("googletagmanager.com", html)
        self.assertNotIn('aria-label="X (Twitter)"', html)


class BannerFileStorageTest(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_delete_banner_removes_file(self):
        banner = Banner.objects.create(
            title="Banner", image=make_image("banner.png")
        )
        path = banner.image.path
        self.assertTrue(os.path.exists(path))

        banner.delete()

        self.assertFalse(os.path.exists(path))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_update_banner_removes_old_file(self):
        banner = Banner.objects.create(
            title="Banner", image=make_image("b1.png")
        )
        old_path = banner.image.path

        banner.image = make_image("b2.png")
        banner.save()

        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(banner.image.path))

class HomeSectionsTest(TestCase):
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
        self.old = Figure.objects.create(
            name="Old Figure",
            slug="old-figure",
            description="Antiga.",
            price=Decimal("100.00"),
            stock=3,
            image=make_image("old.png"),
        )
        self.new = Figure.objects.create(
            name="New Figure",
            slug="new-figure",
            description="Nova.",
            price=Decimal("200.00"),
            stock=3,
            image=make_image("new.png"),
        )
        self.promo = Figure.objects.create(
            name="Promo Figure",
            slug="promo-figure",
            description="Promo.",
            price=Decimal("300.00"),
            stock=3,
            discount_percent=15,
            image=make_image("promo.png"),
        )
        self.sold_promo = Figure.objects.create(
            name="Sold Promo",
            slug="sold-promo",
            description="Esgotada.",
            price=Decimal("400.00"),
            stock=0,
            sold_out=True,
            discount_percent=50,
            image=make_image("sold.png"),
        )

    def test_new_releases_ordered_by_recent(self):
        response = self.client.get(reverse("website:home"))
        releases = list(response.context["new_releases"])
        self.assertEqual(releases[0], self.sold_promo)
        self.assertIn(self.old, releases)
        self.assertContains(response, "Novos")
        self.assertContains(response, "Lançamentos")

    def test_promotions_excludes_sold_out_and_plain(self):
        response = self.client.get(reverse("website:home"))
        promos = list(response.context["promotions"])
        self.assertEqual(promos, [self.promo])
        self.assertContains(response, "Promoções")
        self.assertContains(response, "15% OFF")
