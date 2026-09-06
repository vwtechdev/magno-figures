import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from apps.categories.gating import (
    filter_nsfw_figures,
    is_age_verified,
    redirect_to_age_gate,
)
from apps.categories.models import Category
from apps.figures.models import Figure, StockAlert
from apps.figures.services import calculate_shipping
from apps.website.models import Website

ZIP_CODE_RE = re.compile(r"^\d{5}-?\d{3}$")


def _parse_price(value):
    if value is None:
        return None
    text = value.strip().replace(",", ".")
    if not text:
        return None
    try:
        price = Decimal(text)
    except InvalidOperation:
        return None
    if price < 0:
        return None
    return price


def figure_list_view(request):
    query = request.GET.get("q", "").strip()
    figures = Figure.objects.active().select_related().prefetch_related(
        "categories", "images"
    )
    if query:
        figures = figures.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    selected_slugs = [slug for slug in request.GET.getlist("cat") if slug]
    selected = Category.objects.active().filter(slug__in=selected_slugs)
    selected_slugs = list(selected.values_list("slug", flat=True))
    if selected_slugs:
        category_ids = set()
        for category in selected:
            category_ids.update(
                category.get_descendants(include_self=True).values_list(
                    "pk", flat=True
                )
            )
        figures = figures.filter(categories__in=category_ids).distinct()
    min_price = _parse_price(request.GET.get("min_price"))
    max_price = _parse_price(request.GET.get("max_price"))
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price
    if min_price is not None:
        figures = figures.filter(price__gte=min_price)
    if max_price is not None:
        figures = figures.filter(price__lte=max_price)
    figures = filter_nsfw_figures(request, figures)
    page_obj = Paginator(
        figures, settings.FIGURES_PER_PAGE
    ).get_page(request.GET.get("page"))
    page_query = request.GET.copy()
    page_query.pop("page", None)
    needs_verification = not is_age_verified(request) and any(
        category.is_nsfw_effective for category in selected
    )
    context = {
        "figures": page_obj.object_list,
        "page_obj": page_obj,
        "page_query": page_query.urlencode(),
        "query": query,
        "filter_categories": Category.objects.active().order_by(
            "tree_id", "lft"
        ),
        "selected_cats": selected_slugs,
        "min_price": (request.GET.get("min_price") or "").strip(),
        "max_price": (request.GET.get("max_price") or "").strip(),
        "needs_verification": needs_verification,
    }
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "html": render_to_string(
                    "figures/_results.html", context, request=request
                ),
                "count": page_obj.paginator.count,
            }
        )
    return render(request, "figures/list.html", context)


def figure_detail_view(request, slug):
    figure = Figure.objects.active().prefetch_related(
        "categories", "images"
    ).get(slug=slug)
    if figure.is_nsfw and not is_age_verified(request):
        return redirect_to_age_gate(request)
    related = filter_nsfw_figures(
        request,
        Figure.objects.active()
        .filter(categories__in=figure.categories.all())
        .exclude(pk=figure.pk)
        .distinct()
        .prefetch_related("images"),
    )[:4]
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
    if figure.is_nsfw and not is_age_verified(request):
        return JsonResponse(
            {"error": "Conteúdo destinado a maiores de 18 anos."}, status=403
        )
    origin_zip = Website.objects.get_config().origin_zip_code or ""

    options, error = calculate_shipping(figure, zipcode, origin_zip)
    if error:
        return JsonResponse({"error": error}, status=503)
    return JsonResponse({"options": options})


def stock_alert_subscribe_view(request, slug):
    figure = get_object_or_404(Figure.objects.active(), slug=slug)
    if not figure.sold_out:
        messages.info(request, "Este item já está disponível.")
        return redirect("figures:detail", slug=figure.slug)
    if request.method != "POST":
        return redirect("figures:detail", slug=figure.slug)
    email = (request.POST.get("email") or "").strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Informe um email válido.")
        return redirect("figures:detail", slug=figure.slug)
    try:
        alert, created = StockAlert.objects.get_or_create(
            figure=figure, email=email
        )
    except IntegrityError:
        messages.info(request, "Este email já está na lista de avisos.")
        return redirect("figures:detail", slug=figure.slug)
    if not created and not alert.is_notified:
        messages.info(request, "Este email já está na lista de avisos.")
    else:
        if not created and alert.is_notified:
            alert.is_notified = False
            alert.save(update_fields=["is_notified", "updated_by"])
        messages.success(
            request,
            "Email cadastrado! Avisaremos quando estiver disponível.",
        )
    return redirect("figures:detail", slug=figure.slug)


def stock_alert_unsubscribe_view(request, token):
    from django.core import signing

    from apps.figures.notifications import parse_stock_alert_token

    try:
        data = parse_stock_alert_token(token)
    except signing.BadSignature:
        return render(
            request, "figures/unsubscribe.html", {"valid": False}, status=400
        )
    StockAlert.objects.filter(
        figure_id=data.get("figure_id"), email=data.get("email")
    ).delete()
    return render(
        request,
        "figures/unsubscribe.html",
        {"valid": True, "email": data.get("email")},
    )