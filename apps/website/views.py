from django.shortcuts import render

from apps.figures.models import Figure
from apps.website.models import Banner


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