import re
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.addresses.forms import AddressForm
from apps.addresses.models import Address
from apps.carts.views import clear_cart, get_cart_items, merge_session_cart
from apps.categories.gating import is_age_verified, redirect_to_age_gate
from apps.figures.services import cart_shipping_options
from apps.figures.views import ZIP_CODE_RE
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.website.models import Website
from core.mail import send_mail_async
from core.utils import site_base_url
from core.validators import is_valid_cpf

SHIPPING_COMBINE = "combine"
SHIPPING_COMBINE_LABEL = "A combinar"


def _cart_has_nsfw(request):
    return any(
        item["figure"].is_nsfw for item in get_cart_items(request)
    )


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
    order_pk = order.pk
    user_name = order.user.name
    user_email = order.user.email
    user_phone = order.user.phone
    items_text = "".join(
        f"- {item.quantity}x {item.figure.name} — R$ {item.price:.2f}\n"
        for item in order.items.select_related("figure").all()
    )
    address_text = order.address.full_address
    total = order.total
    subject = f"Novo pedido #{order_pk} no site"
    body = (
        f"Novo pedido recebido.\n\n"
        f"Pedido: #{order_pk}\n"
        f"Cliente: {user_name} ({user_email})\n"
        f"Telefone: {user_phone}\n\n"
        f"Itens:\n{items_text}\n"
        f"Endereço:\n{address_text}\n\n"
        f"Total: R$ {total:.2f}\n\n"
        f"Gerencie em: {site_base_url()}/admin/orders/order/{order_pk}/change/"
    )

    def _dispatch():
        send_mail_async(
            subject,
            body,
            [recipient],
            from_email=settings.DEFAULT_FROM_EMAIL,
        )

    transaction.on_commit(_dispatch)


def _checkout_context(request, addresses, address_form, selected_id, selected_address=None):
    items = get_cart_items(request)
    subtotal = sum(item["figure"].sale_price * item["quantity"] for item in items)
    return {
        "addresses": addresses,
        "selected_id": selected_id,
        "selected_address": selected_address,
        "address_form": address_form,
        "cart_items": items,
        "subtotal": subtotal,
        "has_cpf": bool(request.user.cpf),
    }


@login_required
def checkout_shipping_view(request):
    merge_session_cart(request)
    zipcode = (request.GET.get("zipcode") or "").strip()
    if not ZIP_CODE_RE.fullmatch(zipcode):
        return JsonResponse({"error": "Informe um CEP válido."}, status=400)
    items = get_cart_items(request)
    if not items:
        return JsonResponse({"error": "Seu carrinho está vazio."}, status=400)
    if not is_age_verified(request) and any(
        item["figure"].is_nsfw for item in items
    ):
        return JsonResponse(
            {"error": "Conteúdo destinado a maiores de 18 anos."}, status=403
        )
    origin = Website.objects.get_config().origin_zip_code or ""
    options, error = cart_shipping_options(items, zipcode, origin)
    if error:
        return JsonResponse({"error": error}, status=503)
    return JsonResponse({"options": options})


@login_required
def checkout_view(request):
    merge_session_cart(request)
    if not is_age_verified(request) and _cart_has_nsfw(request):
        messages.error(
            request,
            "Seu carrinho contém itens para maiores de 18 anos. "
            "Confirme sua idade para continuar.",
        )
        return redirect_to_age_gate(request, next_url=reverse("orders:checkout"))
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
                context = _checkout_context(
                    request, addresses, address_form, "new"
                )
                context["error"] = "Verifique os dados do endereço."
                return render(request, "orders/checkout.html", context)
            address = address_form.save(commit=False)
            address.user = request.user
            address.save()
            addresses = Address.objects.filter(user=request.user, is_active=True)

        items = get_cart_items(request)
        if not items:
            messages.info(request, "Seu carrinho está vazio.")
            return redirect("carts:detail")

        sold_item = next(
            (item["figure"] for item in items if item["figure"].sold_out), None
        )
        if sold_item:
            context = _checkout_context(request, addresses, address_form, "new")
            context["error"] = (
                f"O item {sold_item.name} está esgotado e não pode ser comprado. "
                "Remova-o do carrinho."
            )
            return render(request, "orders/checkout.html", context)

        if request.user.cpf:
            cpf = request.user.cpf
        else:
            cpf = re.sub(r"\D", "", request.POST.get("cpf", ""))
            if not is_valid_cpf(cpf):
                context = _checkout_context(request, addresses, address_form, "new")
                context["error"] = "Informe um CPF válido."
                return render(request, "orders/checkout.html", context)
            request.user.cpf = cpf
            request.user.save(update_fields=["cpf"])

        shipping_service = request.POST.get("shipping_service", "").strip()
        origin = Website.objects.get_config().origin_zip_code or ""
        options, error = cart_shipping_options(items, address.zip_code, origin)
        if error:
            if shipping_service != SHIPPING_COMBINE:
                context = _checkout_context(request, addresses, address_form, "new")
                context["error"] = error
                return render(request, "orders/checkout.html", context)
            shipping_service = SHIPPING_COMBINE_LABEL
            shipping_price = None
        else:
            shipping_option = next(
                (option for option in options if option["name"] == shipping_service),
                None,
            )
            if not shipping_option:
                context = _checkout_context(request, addresses, address_form, "new")
                context["error"] = "Selecione uma opção de frete válida."
                return render(request, "orders/checkout.html", context)
            shipping_price = Decimal(str(shipping_option["price"]))

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                address=address,
                shipping_service=shipping_service,
                shipping_price=shipping_price,
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    figure=item["figure"],
                    quantity=item["quantity"],
                    price=item["figure"].sale_price,
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
        _checkout_context(
            request,
            addresses,
            address_form,
            selected_address.pk if selected_address else None,
            selected_address,
        ),
    )
