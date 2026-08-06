from django.shortcuts import render


def cart_detail_view(request):
    return render(request, "carts/detail.html")


def add_to_cart_view(request, figure_id):
    pass


def remove_from_cart_view(request, item_id):
    pass
