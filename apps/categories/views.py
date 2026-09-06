from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.gating import (
    AGE_VERIFIED_SESSION_KEY,
    is_age_verified,
    redirect_to_age_gate,
    safe_next_url,
)
from apps.categories.models import Category
from apps.figures.models import Figure


def age_gate_view(request):
    next_url = safe_next_url(request)
    if request.method == "POST":
        if request.POST.get("confirm") == "yes":
            request.session[AGE_VERIFIED_SESSION_KEY] = True
            return redirect(next_url)
        return redirect("/")
    if is_age_verified(request):
        return redirect(next_url)
    return render(request, "categories/age_gate.html", {"next": next_url})


def category_list_view(request):
    context = {
        "categories": Category.objects.active(),
    }
    return render(request, "categories/list.html", context)


def category_detail_view(request, slug):
    category = get_object_or_404(
        Category.objects.active(), slug=slug
    )
    if category.is_nsfw_effective and not is_age_verified(request):
        return redirect_to_age_gate(request)
    categories = [category] + list(category.get_descendants(include_self=False))
    figures = (
        Figure.objects.active()
        .filter(categories__in=categories)
        .distinct()
        .prefetch_related("categories", "images")
    )
    page_obj = Paginator(
        figures, settings.FIGURES_PER_PAGE
    ).get_page(request.GET.get("page"))
    page_query = request.GET.copy()
    page_query.pop("page", None)
    context = {
        "category": category,
        "figures": page_obj.object_list,
        "page_obj": page_obj,
        "page_query": page_query.urlencode(),
    }
    return render(request, "categories/detail.html", context)