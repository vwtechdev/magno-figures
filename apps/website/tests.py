from io import BytesIO

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.website.models import Website


def make_image(name="website.png"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class WebsiteSeoTest(TestCase):
    def setUp(self):
        cache.clear()
        Website.objects.create(
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