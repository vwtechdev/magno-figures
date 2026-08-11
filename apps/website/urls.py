from django.urls import path

from apps.website import views

app_name = "website"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("about/", views.about_view, name="about"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("terms/", views.terms_view, name="terms"),
]