from django.shortcuts import render


def figure_list_view(request):
    return render(request, "figures/list.html")


def figure_detail_view(request, slug):
    return render(request, "figures/detail.html")
