from django.shortcuts import render


def order_list_view(request):
    return render(request, "orders/list.html")


def order_detail_view(request, pk):
    return render(request, "orders/detail.html")


def checkout_view(request):
    return render(request, "orders/checkout.html")
