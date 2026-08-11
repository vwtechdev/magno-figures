from django.urls import path

from apps.orders import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list_view, name="list"),
    path("<int:pk>/", views.order_detail_view, name="detail"),
    path("<int:pk>/cancel/", views.order_cancel_view, name="cancel"),
    path("checkout/", views.checkout_view, name="checkout"),
]
