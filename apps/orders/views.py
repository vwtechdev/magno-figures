from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.addresses.forms import AddressForm
from apps.addresses.models import Address
from apps.carts.views import clear_cart, get_cart_items, merge_session_cart
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.website.models import Website
from core.mail import send_mail_async
from core.utils import site_base_url


@login_required
def order_list_view(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "items__figure", "items__figure__images")
        .order_by("-created_at")
    )
    return render(request, "orders/list.html", {"orders": orders})


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
        user=request.user,
    )
    return render(request, "orders/detail.html", {"order": order})


@login_required
def order_cancel_view(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == "POST" and order.can_cancel:
        order.status = OrderStatus.CANCELED
        order.save()
        messages.success(request, "Pedido cancelado com sucesso.")
    return redirect("orders:detail", pk=order.pk)


def _notify_admin_new_order(order):
    recipient = Website.objects.get_config().email
    if not recipient:
        return
    items_text = "".join(
        f"- {item.quantity}x {item.figure.name} — R$ {item.price:.2f}\n"
        for item in order.items.select_related("figure").all()
    )
    subject = f"Novo pedido #{order.pk} no site"
    body = (
        f"Novo pedido recebido.\n\n"
        f"Pedido: #{order.pk}\n"
        f"Cliente: {order.user.name} ({order.user.email})\n"
        f"Telefone: {order.user.phone}\n\n"
        f"Itens:\n{items_text}\n"
        f"Endereço:\n{order.address.full_address}\n\n"
        f"Total: R$ {order.total:.2f}\n\n"
        f"Gerencie em: {site_base_url()}/admin/orders/order/{order.pk}/change/"
    )
    send_mail_async(
        subject,
        body,
        [recipient],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


@login_required
def checkout_view(request):
    merge_session_cart(request)
    addresses = Address.objects.filter(user=request.user, is_active=True)
    selected_id = request.session.get("checkout_address_id")
    address_form = AddressForm()

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        if address_id and address_id != "new":
            address = get_object_or_404(
                Address, pk=address_id, user=request.user, is_active=True
            )
        else:
            address_form = AddressForm(request.POST)
            if not address_form.is_valid():
                return render(
                    request,
                    "orders/checkout.html",
                    {
                        "addresses": addresses,
                        "address_form": address_form,
                        "selected_id": "new",
                        "error": "Verifique os dados do endereço.",
                    },
                )
            address = address_form.save(commit=False)
            address.user = request.user
            address.save()
            addresses = Address.objects.filter(user=request.user, is_active=True)

        items = get_cart_items(request)
        if not items:
            messages.info(request, "Seu carrinho está vazio.")
            return redirect("carts:detail")

        with transaction.atomic():
            order = Order.objects.create(user=request.user, address=address)
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    figure=item["figure"],
                    quantity=item["quantity"],
                    price=item["figure"].price,
                )
            clear_cart(request)

        _notify_admin_new_order(order)
        return redirect(order.get_whatsapp_url())

    selected_address = None
    if selected_id:
        selected_address = Address.objects.filter(
            pk=selected_id, user=request.user, is_active=True
        ).first()

    return render(
        request,
        "orders/checkout.html",
        {
            "addresses": addresses,
            "selected_id": selected_address.pk if selected_address else None,
            "selected_address": selected_address,
            "address_form": address_form,
        },
    )
