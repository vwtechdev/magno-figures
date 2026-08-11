import re

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.figures.models import Figure
from apps.figures.services import calculate_shipping
from apps.website.models import Website

ZIP_CODE_RE = re.compile(r"^\d{5}-?\d{3}$")


def figure_list_view(request):
    query = request.GET.get("q", "").strip()
    figures = Figure.objects.active().select_related().prefetch_related(
        "categories", "images"
    )
    if query:
        figures = figures.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    page_obj = Paginator(
        figures, settings.FIGURES_PER_PAGE
    ).get_page(request.GET.get("page"))
    page_query = request.GET.copy()
    page_query.pop("page", None)
    context = {
        "figures": page_obj.object_list,
        "page_obj": page_obj,
        "page_query": page_query.urlencode(),
        "query": query,
    }
    return render(request, "figures/list.html", context)


def figure_detail_view(request, slug):
    figure = Figure.objects.active().prefetch_related(
        "categories", "images"
    ).get(slug=slug)
    related = (
        Figure.objects.active()
        .filter(categories__in=figure.categories.all())
        .exclude(pk=figure.pk)
        .distinct()
        .prefetch_related("images")[:4]
    )
    context = {
        "figure": figure,
        "related": related,
    }
    return render(request, "figures/detail.html", context)


def figure_shipping_view(request, slug):
    if request.method != "GET":
        return JsonResponse({"error": "Método não permitido."}, status=405)

    zipcode = (request.GET.get("zipcode") or "").strip()
    if not ZIP_CODE_RE.fullmatch(zipcode):
        return JsonResponse({"error": "Informe um CEP válido."}, status=400)

    figure = get_object_or_404(Figure.objects.active(), slug=slug)
    origin_zip = Website.objects.get_config().origin_zip_code or ""

    options, error = calculate_shipping(figure, zipcode, origin_zip)
    if error:
        return JsonResponse({"error": error}, status=503)
    return JsonResponse({"options": options})