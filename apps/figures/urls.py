from django.urls import path

from apps.figures import views

app_name = "figures"

urlpatterns = [
    path("", views.figure_list_view, name="list"),
    path("<slug:slug>/", views.figure_detail_view, name="detail"),
]
