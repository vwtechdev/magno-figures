from django.shortcuts import render


def category_list_view(request):
    return render(request, "categories/list.html")


def category_detail_view(request, slug):
    return render(request, "categories/detail.html")
