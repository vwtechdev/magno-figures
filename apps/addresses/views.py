from django.shortcuts import render


def address_list_view(request):
    return render(request, "addresses/list.html")
