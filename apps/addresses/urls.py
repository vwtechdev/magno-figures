from django.urls import path

from apps.addresses import views

app_name = "addresses"

urlpatterns = [
    path("", views.address_list_view, name="list"),
    path("new/", views.address_form_view, name="create"),
    path("edit/<int:pk>/", views.address_form_view, name="update"),
    path("delete/<int:pk>/", views.address_delete_view, name="delete"),
    path("primary/<int:pk>/", views.address_set_primary_view, name="set-primary"),
]
