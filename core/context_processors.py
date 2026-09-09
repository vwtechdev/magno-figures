from django.conf import settings

from apps.carts.models import Cart
from apps.categories.gating import get_nsfw_category_ids
from apps.categories.models import Category
from apps.website.models import Website
from core.utils import site_base_url


def global_context(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.item_count
    else:
        cart_count = sum((request.session.get("cart") or {}).values())
    nav_categories = Category.objects.active().order_by("level", "name")
    nsfw_ids = get_nsfw_category_ids()
    if nsfw_ids:
        nav_categories = nav_categories.exclude(pk__in=nsfw_ids)
    return {
        "website_config": Website.objects.get_config(),
        "cart_count": cart_count,
        "nav_categories": nav_categories,
        "site_url": site_base_url(),
    }