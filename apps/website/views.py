from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from apps.categories.models import Category
from apps.figures.models import Figure
from apps.website.models import Banner
from core.utils import site_base_url


def home_view(request):
    context = {
        "banners": Banner.objects.active(),
        "figures": Figure.objects.active().prefetch_related("categories", "images"),
    }
    return render(request, "website/home.html", context)


def about_view(request):
    return render(request, "website/about.html")


def privacy_view(request):
    return render(request, "website/privacy.html")


def terms_view(request):
    return render(request, "website/terms.html")


def robots_txt_view(request):
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {site_base_url()}/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


def sitemap_view(request):
    base = site_base_url()
    entries = []
    for path in ("/", "/figures/", "/about/", "/privacy/", "/terms/"):
        entries.append(
            {"loc": base + path, "changefreq": "weekly", "priority": "0.8"}
        )
    for figure in Figure.objects.active().order_by("-updated_at"):
        entries.append(
            {
                "loc": base + reverse("figures:detail", args=[figure.slug]),
                "lastmod": figure.updated_at.date().isoformat(),
                "changefreq": "weekly",
                "priority": "0.8",
            }
        )
    for category in Category.objects.active().order_by("-updated_at"):
        entries.append(
            {
                "loc": base + reverse("categories:detail", args=[category.slug]),
                "lastmod": category.updated_at.date().isoformat(),
            }
        )
    xml = render_to_string("website/sitemap.xml", {"entries": entries})
    return HttpResponse(xml, content_type="application/xml")