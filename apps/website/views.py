from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from apps.categories.gating import (
    filter_nsfw_categories,
    filter_nsfw_figures,
    filter_nsfw_figures_selected,
)
from apps.categories.models import Category
from apps.figures.models import Figure
from apps.website.models import Banner
from core.utils import site_base_url


def home_view(request):
    visible_figures = filter_nsfw_figures_selected(
        request,
        Figure.objects.active().prefetch_related("categories", "images"),
        [],
    )
    context = {
        "banners": Banner.objects.active(),
        "figures": visible_figures.filter(discount_percent=0),
        "new_releases": visible_figures.filter(discount_percent=0).order_by(
            "-created_at"
        )[:10],
        "promotions": visible_figures.filter(
            discount_percent__gt=0, sold_out=False
        ).order_by("-discount_percent", "-created_at")[:10],
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
        "Disallow: /accounts/\n"
        "Disallow: /orders/\n"
        "Disallow: /carts/\n"
        "Disallow: /addresses/\n"
        "Disallow: /newsletter/\n"
        "Disallow: /categories/age-verification/\n"
        "Disallow: /figures/stock-alerts/unsubscribe/\n"
        "Disallow: /figures/*/notify-when-available/\n"
        "Disallow: /figures/*/shipping/\n"
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
    for figure in filter_nsfw_figures(
        request, Figure.objects.active().order_by("-updated_at")
    ):
        entries.append(
            {
                "loc": base + reverse("figures:detail", args=[figure.slug]),
                "lastmod": figure.updated_at.date().isoformat(),
                "changefreq": "weekly",
                "priority": "0.8",
            }
        )
    for category in filter_nsfw_categories(
        request, Category.objects.active().order_by("-updated_at")
    ):
        entries.append(
            {
                "loc": base + reverse("categories:detail", args=[category.slug]),
                "lastmod": category.updated_at.date().isoformat(),
            }
        )
    xml = render_to_string("website/sitemap.xml", {"entries": entries})
    return HttpResponse(xml, content_type="application/xml")