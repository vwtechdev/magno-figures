from django.urls import path

from apps.figures import views

app_name = "figures"

urlpatterns = [
    path("", views.figure_list_view, name="list"),
    path("<slug:slug>/shipping/", views.figure_shipping_view, name="shipping"),
    path(
        "<slug:slug>/notify-when-available/",
        views.stock_alert_subscribe_view,
        name="notify",
    ),
    path(
        "stock-alerts/unsubscribe/<str:token>/",
        views.stock_alert_unsubscribe_view,
        name="unsubscribe",
    ),
    path("<slug:slug>/", views.figure_detail_view, name="detail"),
]
