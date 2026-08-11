from django.urls import path

from apps.carts import views

app_name = "carts"

urlpatterns = [
    path("", views.cart_detail_view, name="detail"),
    path("add/<int:figure_id>/", views.add_to_cart_view, name="add"),
    path("update/<int:figure_id>/", views.update_cart_view, name="update"),
    path("remove/<int:figure_id>/", views.remove_from_cart_view, name="remove"),
]
