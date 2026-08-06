from django.urls import path

from apps.orders import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list_view, name="list"),
    path("<int:pk>/", views.order_detail_view, name="detail"),
    path("finalizar/", views.checkout_view, name="checkout"),
]
