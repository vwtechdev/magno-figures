from django.urls import path

from apps.newsletters import views

app_name = "newsletters"

urlpatterns = [
    path("subscribe/", views.subscribe_view, name="subscribe"),
    path(
        "unsubscribe/<str:token>/",
        views.unsubscribe_view,
        name="unsubscribe",
    ),
    path(
        "stock-alerts/unsubscribe/<str:token>/",
        views.stock_alert_unsubscribe_view,
        name="stock_alert_unsubscribe",
    ),
]
