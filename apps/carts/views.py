from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.carts.models import Cart, CartItem
from apps.figures.models import Figure

SESSION_CART_KEY = "cart"


def _get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def _session_cart(request):
    return request.session.setdefault(SESSION_CART_KEY, {})


def merge_session_cart(request):
    if not request.user.is_authenticated:
        return
    session_cart = request.session.get(SESSION_CART_KEY)
    if not session_cart:
        return
    cart = _get_user_cart(request.user)
    for figure_id, quantity in session_cart.items():
        try:
            figure = Figure.objects.get(pk=int(figure_id), is_active=True)
        except (Figure.DoesNotExist, ValueError):
            continue
        if figure.sold_out:
            continue
        item, created = CartItem.objects.get_or_create(
            cart=cart, figure=figure, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity", "updated_by"])
    del request.session[SESSION_CART_KEY]
    request.session.modified = True


def cart_is_empty(request):
    if request.user.is_authenticated:
        return not _get_user_cart(request.user).items.exists()
    return not request.session.get(SESSION_CART_KEY)


def add_to_cart_view(request, figure_id):
    figure = get_object_or_404(Figure, pk=figure_id, is_active=True)
    if figure.sold_out:
        messages.error(
            request,
            "Este item está esgotado e não pode ser adicionado ao carrinho.",
        )
        return redirect(request.META.get("HTTP_REFERER") or "figures:list")
    was_empty = cart_is_empty(request)

    if request.user.is_authenticated:
        merge_session_cart(request)
        item, created = CartItem.objects.get_or_create(
            cart=_get_user_cart(request.user), figure=figure, defaults={"quantity": 1}
        )
        if not created:
            new_quantity = item.quantity + 1
            if figure.in_stock:
                new_quantity = min(new_quantity, figure.stock)
            item.quantity = new_quantity
            item.save(update_fields=["quantity", "updated_by"])
    else:
        session_cart = _session_cart(request)
        key = str(figure.id)
        new_quantity = session_cart.get(key, 0) + 1
        if figure.in_stock:
            new_quantity = min(new_quantity, figure.stock)
        session_cart[key] = new_quantity
        request.session.modified = True

    if request.GET.get("buy") and was_empty:
        return redirect("orders:checkout")
    return redirect(request.META.get("HTTP_REFERER") or "figures:list")


def get_cart_items(request):
    if request.user.is_authenticated:
        items = [
            {
                "figure": item.figure,
                "quantity": item.quantity,
                "total": item.figure.price * item.quantity,
            }
            for item in _get_user_cart(request.user).items.select_related("figure").order_by("-created_at")
        ]
    else:
        items = []
        session_cart = request.session.get(SESSION_CART_KEY) or {}
        figures = Figure.objects.in_bulk(
            [int(fid) for fid in session_cart if str(fid).isdigit()]
        )
        for figure_id, quantity in session_cart.items():
            if not str(figure_id).isdigit():
                continue
            figure = figures.get(int(figure_id))
            if figure and figure.is_active:
                items.append(
                    {
                        "figure": figure,
                        "quantity": quantity,
                        "total": figure.price * quantity,
                    }
                )
    return items


def cart_detail_view(request):
    merge_session_cart(request)
    items = get_cart_items(request)
    subtotal = sum(item["figure"].price * item["quantity"] for item in items)
    return render(
        request,
        "carts/detail.html",
        {"cart_items": items, "subtotal": subtotal, "cart_empty": not items},
    )


def _apply_quantity(current, action, qty, figure):
    if qty is not None and str(qty).isdigit():
        new_quantity = max(int(qty), 1)
        if figure.in_stock:
            new_quantity = min(new_quantity, figure.stock)
        if figure.sold_out and new_quantity > current:
            return current
        return new_quantity
    if action == "inc":
        if figure.sold_out:
            return current
        new_quantity = current + 1
        if figure.in_stock:
            new_quantity = min(new_quantity, figure.stock)
        return new_quantity
    if action == "dec":
        if current <= 1:
            return 0
        return current - 1
    return current


def update_cart_view(request, figure_id):
    figure = get_object_or_404(Figure, pk=figure_id, is_active=True)
    action = request.POST.get("action")
    qty = request.POST.get("qty")

    if request.user.is_authenticated:
        merge_session_cart(request)
        item = CartItem.objects.filter(
            cart=_get_user_cart(request.user), figure=figure
        ).first()
        if item is None:
            return redirect("carts:detail")
        new_quantity = _apply_quantity(item.quantity, action, qty, figure)
        if new_quantity <= 0:
            item.delete()
        else:
            item.quantity = new_quantity
            item.save(update_fields=["quantity", "updated_by"])
    else:
        session_cart = _session_cart(request)
        key = str(figure.id)
        if key not in session_cart:
            return redirect("carts:detail")
        new_quantity = _apply_quantity(session_cart[key], action, qty, figure)
        if new_quantity <= 0:
            del session_cart[key]
        else:
            session_cart[key] = new_quantity
        request.session.modified = True

    return redirect("carts:detail")


def clear_cart(request):
    if request.user.is_authenticated:
        _get_user_cart(request.user).items.all().delete()
    else:
        request.session.pop(SESSION_CART_KEY, None)
        request.session.modified = True


def remove_from_cart_view(request, figure_id):
    figure = get_object_or_404(Figure, pk=figure_id, is_active=True)

    if request.user.is_authenticated:
        merge_session_cart(request)
        CartItem.objects.filter(
            cart=_get_user_cart(request.user), figure=figure
        ).delete()
    else:
        session_cart = _session_cart(request)
        session_cart.pop(str(figure.id), None)
        request.session.modified = True

    return redirect("carts:detail")
