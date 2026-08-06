from django.urls import path

from apps.carts import views

app_name = "carts"

urlpatterns = [
    path("", views.cart_detail_view, name="detail"),
    path("adicionar/<int:figure_id>/", views.add_to_cart_view, name="add"),
    path("remover/<int:item_id>/", views.remove_from_cart_view, name="remove"),
]
