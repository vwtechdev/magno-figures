from django.urls import path

from apps.categories import views

app_name = "categories"

urlpatterns = [
    path("age-verification/", views.age_gate_view, name="age_gate"),
    path("", views.category_list_view, name="list"),
    path("<slug:slug>/", views.category_detail_view, name="detail"),
]
