from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.addresses.forms import AddressForm
from apps.addresses.models import Address


def _profile_addresses_url():
    return f"{reverse('accounts:profile')}?tab=addresses"


class UserAddressesMixin(LoginRequiredMixin):
    """Restringe o queryset aos endereços do usuário logado."""

    model = Address

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressListView(UserAddressesMixin, ListView):
    template_name = "addresses/list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class AddressFormMixin(UserAddressesMixin):
    form_class = AddressForm
    template_name = "addresses/form.html"
    context_object_name = "address"

    def get_success_url(self):
        return _profile_addresses_url()

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AddressCreateView(AddressFormMixin, CreateView):
    pass


class AddressUpdateView(AddressFormMixin, UpdateView):
    pass


class AddressDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Address
    context_object_name = "address"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def test_func(self):
        self.get_object()
        return True

    def get_success_url(self):
        return _profile_addresses_url()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return redirect(self.get_success_url())

    def form_valid(self, form):
        address = self.object
        was_primary = address.is_primary
        address.is_active = False
        address.save(update_fields=["is_active", "updated_by"])
        if was_primary:
            next_address = (
                self.get_queryset()
                .filter(is_active=True)
                .exclude(pk=address.pk)
                .order_by("-created_at")
                .first()
            )
            if next_address:
                next_address.is_primary = True
                next_address.save(update_fields=["is_primary", "updated_by"])
        return redirect(self.get_success_url())


@login_required
def address_set_primary_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        address.is_primary = True
        address.save(update_fields=["is_primary", "updated_by"])
    return redirect(_profile_addresses_url())
