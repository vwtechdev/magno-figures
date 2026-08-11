from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.addresses.forms import AddressForm
from apps.addresses.models import Address


def _profile_addresses_url():
    return f"{reverse('accounts:profile')}?tab=addresses"


@login_required
def address_list_view(request):
    addresses = Address.objects.filter(user=request.user, is_active=True)
    return render(request, "addresses/list.html", {"addresses": addresses})


@login_required
def address_form_view(request, pk=None):
    if pk:
        address = get_object_or_404(Address, pk=pk, user=request.user)
    else:
        address = None

    form = AddressForm(request.POST or None, instance=address)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        address.save()
        return redirect(_profile_addresses_url())

    return render(request, "addresses/form.html", {"form": form, "address": address})


@login_required
def address_delete_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        was_primary = address.is_primary
        address.is_active = False
        address.save(update_fields=["is_active", "updated_by"])
        if was_primary:
            next_address = (
                Address.objects.filter(user=request.user, is_active=True)
                .exclude(pk=address.pk)
                .order_by("-created_at")
                .first()
            )
            if next_address:
                next_address.is_primary = True
                next_address.save(update_fields=["is_primary", "updated_by"])
    return redirect(_profile_addresses_url())


@login_required
def address_set_primary_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        address.is_primary = True
        address.save(update_fields=["is_primary", "updated_by"])
    return redirect(_profile_addresses_url())
