import json
import re
from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.figures.models import Figure
from apps.website.models import Website


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
            response, f'<link rel="canonical" href="{settings.BASE_URL}/">'
        )
        self.assertContains(response, '<meta property="og:site_name" content="Magno Figures">')
        self.assertContains(response, '<meta property="og:locale" content="pt_BR">')
        self.assertContains(response, '<meta property="og:type" content="website">')
        self.assertContains(response, f'<meta property="og:url" content="{settings.BASE_URL}/">')
        self.assertContains(
            response,
            f'<meta property="og:image" content="{settings.BASE_URL}{self.website.logo.url}">',
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
            f"Sitemap: {settings.BASE_URL}/sitemap.xml", response.content.decode()
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
        self.assertIn(f"<loc>{settings.BASE_URL}/figures/</loc>", content)
        self.assertIn(f"<loc>{settings.BASE_URL}/about/</loc>", content)
        self.assertIn(f"<loc>{settings.BASE_URL}/figures/figure-seo/</loc>", content)


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