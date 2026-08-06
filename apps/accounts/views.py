from django.contrib.auth import login, logout
from django.shortcuts import redirect, render


def login_view(request):
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("website:home")


def register_view(request):
    return render(request, "accounts/register.html")


def profile_view(request):
    return render(request, "accounts/profile.html")
