import json
import re
from io import BytesIO

from PIL import Image
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.categories.models import Category
from apps.website.models import Website


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
        self.assertContains(response, f'"{settings.BASE_URL}/categories/filha/"')