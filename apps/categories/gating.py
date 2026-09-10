from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

AGE_VERIFIED_SESSION_KEY = "age_verified"


def is_age_verified(request):
    return bool(request.session.get(AGE_VERIFIED_SESSION_KEY))


def get_nsfw_category_ids():
    from apps.categories.models import Category

    ids = set(
        Category.objects.filter(is_nsfw=True).values_list("pk", flat=True)
    )
    for category in Category.objects.filter(is_nsfw=True):
        ids.update(
            category.get_descendants(include_self=False).values_list(
                "pk", flat=True
            )
        )
    return ids


def filter_nsfw_figures(request, queryset):
    if is_age_verified(request):
        return queryset
    nsfw_ids = get_nsfw_category_ids()
    if not nsfw_ids:
        return queryset
    return queryset.exclude(categories__in=nsfw_ids).distinct()


def show_nsfw_figures(request, selected_categories):
    """NSFW figures surface only when verified AND an NSFW category is selected."""
    if not is_age_verified(request):
        return False
    return any(
        category.is_nsfw_effective for category in selected_categories
    )


def filter_nsfw_figures_selected(request, queryset, selected_categories):
    if show_nsfw_figures(request, selected_categories):
        return queryset
    nsfw_ids = get_nsfw_category_ids()
    if not nsfw_ids:
        return queryset
    return queryset.exclude(categories__in=nsfw_ids).distinct()


def filter_nsfw_categories(request, queryset):
    if is_age_verified(request):
        return queryset
    nsfw_ids = get_nsfw_category_ids()
    if not nsfw_ids:
        return queryset
    return queryset.exclude(pk__in=nsfw_ids)


def age_gate_url(request, next_url=None):
    target = next_url or request.get_full_path()
    if not url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        target = "/"
    return f"{reverse('categories:age_gate')}?{urlencode({'next': target})}"


def redirect_to_age_gate(request, next_url=None):
    return redirect(age_gate_url(request, next_url=next_url))


def safe_next_url(request, fallback="/"):
    candidate = (
        request.POST.get("next") or request.GET.get("next") or fallback
    )
    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return fallback
    return candidate
