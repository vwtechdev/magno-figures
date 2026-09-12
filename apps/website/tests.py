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
        self.client.cookies["mf_cookie_consent"] = "granted"
        response = self.client.get(reverse("website:home"))
        self.assertContains(
            response,
            '<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script>',
        )

    def test_google_analytics_absent_without_consent(self):
        response = self.client.get(reverse("website:home"))
        self.assertNotContains(response, "googletagmanager.com")
        self.assertContains(response, 'data-ga="1"')

    def test_google_analytics_absent_when_denied(self):
        self.client.cookies["mf_cookie_consent"] = "denied"
        response = self.client.get(reverse("website:home"))
        self.assertNotContains(response, "googletagmanager.com")

    def test_cookie_bar_has_reject_button(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, 'id="cookieReject"')
        self.assertContains(response, "Recusar")

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
        content = response.content.decode()
        self.assertIn(
            f"Sitemap: {site_base_url()}/sitemap.xml", content
        )
        for disallow in (
            "/accounts/",
            "/orders/",
            "/carts/",
            "/addresses/",
            "/newsletter/",
            "/categories/age-verification/",
            "/figures/stock-alerts/unsubscribe/",
            "/figures/*/notify-when-available/",
            "/figures/*/shipping/",
        ):
            self.assertIn(f"Disallow: {disallow}", content)

    def test_auth_pages_are_noindex(self):
        for path in (
            reverse("accounts:login"),
            reverse("accounts:register"),
            reverse("accounts:password_reset"),
            reverse("categories:age_gate"),
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response,
                '<meta name="robots" content="noindex, nofollow">',
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
        self.assertNotIn(f"<loc>{site_base_url()}/about/</loc>", content)
        self.assertNotIn(f"<loc>{site_base_url()}/privacy/</loc>", content)
        self.assertNotIn(f"<loc>{site_base_url()}/terms/</loc>", content)
        self.assertIn(f"<loc>{site_base_url()}/figures/figure-seo/</loc>", content)

    def test_institutional_pages_are_noindex(self):
        for path in ("/about/", "/privacy/", "/terms/"):
            response = self.client.get(path)
            self.assertContains(
                response,
                '<meta name="robots" content="noindex, nofollow">',
            )


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

    def test_catalog_shows_oldest_ten(self):
        response = self.client.get(reverse("website:home"))
        catalog = list(response.context["figures"])
        self.assertEqual(catalog, [self.old, self.new])
        self.assertNotIn(self.promo, catalog)
        self.assertNotIn(self.sold_promo, catalog)

    def test_new_releases_ordered_by_recent(self):
        response = self.client.get(reverse("website:home"))
        releases = list(response.context["new_releases"])
        self.assertEqual(releases[0], self.new)
        self.assertIn(self.old, releases)
        self.assertNotIn(self.promo, releases)
        self.assertNotIn(self.sold_promo, releases)
        self.assertContains(response, "Lançamentos")

    def test_promotions_excludes_sold_out_and_plain(self):
        response = self.client.get(reverse("website:home"))
        promos = list(response.context["promotions"])
        self.assertEqual(promos, [self.promo])
        self.assertContains(response, "Promoções")
        self.assertContains(response, "15% OFF")


class Custom404Test(TestCase):
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

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["*"])
    def test_custom_404_page(self):
        response = self.client.get("/pagina-que-nao-existe/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Página não encontrada", status_code=404)
        self.assertContains(response, "noindex, nofollow", status_code=404)
        self.assertContains(response, "Voltar à home", status_code=404)


class WebsiteThemeTest(TestCase):
    def setUp(self):
        cache.clear()
        self.website = Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )

    def test_theme_block_absent_when_blank(self):
        response = self.client.get(reverse("website:home"))
        self.assertNotContains(response, 'id="website-theme"')

    def test_theme_block_renders_overrides(self):
        self.website.theme_background = "#112233"
        self.website.theme_buttons = "#EAC979"
        self.website.theme_whatsapp = "#25D366"
        self.website.theme_danger = "#f87171"
        self.website.save()
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, 'id="website-theme"')
        self.assertContains(response, ":root {")
        self.assertContains(response, "--bg: #112233;")
        self.assertContains(response, "--gold-2: #EAC979;")
        self.assertContains(response, "--gold-gradient: #EAC979;")
        self.assertContains(response, "--gold-2-rgb: 234, 201, 121;")
        self.assertContains(response, "--whatsapp-rgb: 37, 211, 102;")
        self.assertContains(response, "--danger-soft:")

    def test_theme_vars_empty_when_blank(self):
        self.assertEqual(Website.objects.get_config().theme_css_vars, {})

    def test_invalid_hex_rejected(self):
        from django.core.exceptions import ValidationError

        self.website.theme_buttons = "dourado"
        with self.assertRaises(ValidationError):
            self.website.full_clean()


class WebsiteConfigEmptyDbTest(TestCase):
    def setUp(self):
        cache.clear()
        Website.objects.all().delete()

    def test_get_config_creates_placeholder_without_images(self):
        config = Website.objects.get_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.pk, 1)
        self.assertFalse(config.logo)
        self.assertFalse(config.favicon)

    def test_home_renders_without_website_config(self):
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "img/logo.png")


class HomeNoBannerTest(TestCase):
    def setUp(self):
        cache.clear()
        Website.objects.all().delete()

    def test_catalog_section_gets_top_padding_without_banners(self):
        Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "catalog--no-hero")

    def test_no_top_padding_class_when_banners_exist(self):
        website = Website.objects.create(
            company_name="Magno Figures",
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )
        Banner.objects.create(
            website=website, title="Banner", image=make_image("banner.png")
        )
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "catalog--no-hero")


class WebsiteSubtitleTitleTest(TestCase):
    def setUp(self):
        cache.clear()

    def _make_website(self, subtitle=""):
        return Website.objects.create(
            company_name="Magno Figures",
            subtitle=subtitle,
            logo=make_image("logo.png"),
            favicon=make_image("favicon.png"),
            whatsapp="5511999999999",
            email="",
            about="Sobre a loja.",
            privacy_policy="Política de privacidade.",
        )

    def test_home_title_uses_subtitle_when_set(self):
        self._make_website(subtitle="O melhor site de action figures")
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, "<title>Magno Figures - O melhor site de action figures</title>")

    def test_home_title_falls_back_without_subtitle(self):
        self._make_website()
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, "<title>Magno Figures — Catálogo de Action Figures</title>")

    def test_get_config_creates_without_subtitle(self):
        Website.objects.all().delete()
        config = Website.objects.get_config()
        self.assertEqual(config.subtitle, "")


class CookieBarTest(TestCase):
    def test_cookie_bar_markup_present(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, 'id="cookieBar"')
        self.assertContains(response, 'id="cookieAccept"')
        self.assertContains(response, "Aceitar cookies")
        self.assertContains(
            response, "Usamos cookies para melhorar sua experiência de compra"
        )
        self.assertContains(response, reverse("website:privacy"))
        self.assertContains(response, "js/website/cookies.js")
