from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from apps.categories.models import Category
from apps.figures.models import Figure


def category_list_view(request):
    context = {
        "categories": Category.objects.active(),
    }
    return render(request, "categories/list.html", context)


def category_detail_view(request, slug):
    category = get_object_or_404(
        Category.objects.active(), slug=slug
    )
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