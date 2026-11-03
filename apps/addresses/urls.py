from django.urls import path

from apps.addresses import views

app_name = "addresses"

urlpatterns = [
    path("", views.AddressListView.as_view(), name="list"),
    path("new/", views.AddressCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", views.AddressUpdateView.as_view(), name="update"),
    path("delete/<int:pk>/", views.AddressDeleteView.as_view(), name="delete"),
    path(
        "primary/<int:pk>/",
        views.address_set_primary_view,
        name="set-primary",
    ),
]
