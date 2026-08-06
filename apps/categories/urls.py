from django.urls import path

from apps.categories import views

app_name = "categories"

urlpatterns = [
    path("", views.category_list_view, name="list"),
    path("<slug:slug>/", views.category_detail_view, name="detail"),
]
