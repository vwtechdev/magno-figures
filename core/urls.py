from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from apps.website.views import robots_txt_view, sitemap_view


def health_check(request):
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check),
    path("robots.txt", robots_txt_view),
    path("sitemap.xml", sitemap_view),
    path("", include("apps.website.urls", namespace="website")),
    path("categories/", include("apps.categories.urls", namespace="categories")),
    path("figures/", include("apps.figures.urls", namespace="figures")),
    path("carts/", include("apps.carts.urls", namespace="carts")),
    path("orders/", include("apps.orders.urls", namespace="orders")),
    path("addresses/", include("apps.addresses.urls", namespace="addresses")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("newsletter/", include("apps.newsletters.urls", namespace="newsletters")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
