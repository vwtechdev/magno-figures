import re
from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.models import User
from apps.addresses.models import Address
from apps.orders.models import Order
from core.mail import send_mail_async
from core.validators import is_valid_cpf


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if not request.POST.get("remember"):
                request.session.set_expiry(0)
            next_url = request.POST.get("next") or request.GET.get("next")
            if not url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                next_url = "website:home"
            return redirect(next_url)
        messages.error(request, "Email ou senha inválidos.")
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("website:home")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("website:home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        errors = []
        if not name:
            errors.append("Informe seu nome.")
        if not email:
            errors.append("Informe seu email.")
        if User.objects.filter(email__iexact=email).exists():
            errors.append("Já existe uma conta com este email.")
        if password1 != password2:
            errors.append("As senhas não coincidem.")
        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                errors.extend(list(exc.messages))

        if errors:
            messages.error(request, " ".join(errors))
            return render(request, "accounts/register.html", {"values": request.POST})

        user = User.objects.create_user(
            email=email, password=password1, name=name, phone=phone
        )
        login(request, user)
        messages.success(request, "Cadastro realizado com sucesso. Bem-vindo!")
        return redirect("website:home")

    return render(request, "accounts/register.html")


def profile_view(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "items__figure", "items__figure__images")
        .order_by("-created_at")
        if request.user.is_authenticated
        else Order.objects.none()
    )
    addresses = (
        Address.objects.filter(user=request.user, is_active=True)
        if request.user.is_authenticated
        else Address.objects.none()
    )
    tab = request.GET.get("tab", "profile")
    if tab not in ("profile", "orders", "addresses"):
        tab = "profile"
    return render(
        request,
        "accounts/profile.html",
        {
            "orders": orders,
            "addresses": addresses,
            "active_tab": tab,
        },
    )


@login_required
def profile_data_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        cpf = re.sub(r"\D", "", request.POST.get("cpf", ""))
        birth_date = None
        birth_date_error = False
        birth_date_raw = request.POST.get("birth_date", "").strip()
        if birth_date_raw:
            try:
                birth_date = date.fromisoformat(birth_date_raw)
                if birth_date > date.today():
                    birth_date_error = True
            except ValueError:
                birth_date_error = True
        if not name:
            messages.error(request, "Informe seu nome.")
        elif cpf and not is_valid_cpf(cpf):
            messages.error(request, "CPF inválido.")
        elif birth_date_error:
            messages.error(request, "Data de nascimento inválida.")
        else:
            request.user.name = name
            request.user.phone = phone
            request.user.cpf = cpf
            request.user.birth_date = birth_date
            request.user.save(
                update_fields=["name", "phone", "cpf", "birth_date"]
            )
            messages.success(request, "Dados atualizados com sucesso.")
    return redirect("accounts:profile")


class AsyncPasswordResetForm(DjangoPasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        send_mail_async(subject, body, [to_email], from_email=from_email)


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    form_class = AsyncPasswordResetForm


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
