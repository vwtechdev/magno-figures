from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health_check(request):
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check),
    path("", include("apps.website.urls", namespace="website")),
    path("categoria/", include("apps.categories.urls", namespace="categories")),
    path("figures/", include("apps.figures.urls", namespace="figures")),
    path("carrinho/", include("apps.carts.urls", namespace="carts")),
    path("pedidos/", include("apps.orders.urls", namespace="orders")),
    path("conta/", include("apps.accounts.urls", namespace="accounts")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
