from django.urls import path
from django.views.generic import TemplateView

from apps.website import views

app_name = "website"

urlpatterns = [
    path("", views.home_view, name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="website/about.html"),
        name="about",
    ),
    path(
        "privacy/",
        TemplateView.as_view(template_name="website/privacy.html"),
        name="privacy",
    ),
    path(
        "terms/",
        TemplateView.as_view(template_name="website/terms.html"),
        name="terms",
    ),
]
