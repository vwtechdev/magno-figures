import re
from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode

from apps.accounts.models import User
from apps.accounts.verification import (
    resend_throttled,
    send_verification_email,
    verification_token_generator,
)
from apps.addresses.models import Address
from apps.orders.models import Order, OrderStatus
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
        pending = (
            User.objects.filter(email__iexact=email).only("pk").first()
            if email
            else None
        )
        if (
            pending is not None
            and not pending.is_active
            and pending.email_verified_at is None
        ):
            messages.error(
                request,
                "Sua conta ainda não foi confirmada. Verifique seu e-mail "
                "ou solicite um novo link.",
            )
            return redirect("accounts:resend_verification")
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
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Informe um email válido.")
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

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password1,
                name=name,
                phone=phone,
                is_active=False,
            )
        send_verification_email(user)
        messages.success(
            request,
            "Cadastro realizado! Enviamos um link de confirmação para o seu email.",
        )
        return redirect("accounts:verification_sent")

    return render(request, "accounts/register.html")


def verification_sent_view(request):
    return render(request, "accounts/verify_sent.html")


def resend_verification_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        user = (
            User.objects.filter(email__iexact=email).first() if email else None
        )
        if (
            user is not None
            and not user.is_active
            and user.email_verified_at is None
            and not resend_throttled(user)
        ):
            send_verification_email(user)
        messages.success(
            request,
            "Se a conta existir e ainda não foi confirmada, "
            "enviamos um novo link para o seu email.",
        )
        return redirect("accounts:verification_sent")
    return render(request, "accounts/verify_resend.html")


def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is not None and user.is_active and user.email_verified_at is not None:
        messages.info(request, "Sua conta já foi confirmada. Faça login.")
        return redirect("accounts:login")
    if (
        user is None
        or not verification_token_generator.check_token(user, token)
    ):
        return render(request, "accounts/verify_invalid.html", status=400)
    user.is_active = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=["is_active", "email_verified_at"])
    login(
        request, user, backend="django.contrib.auth.backends.ModelBackend"
    )
    messages.success(request, "Email confirmado com sucesso. Bem-vindo!")
    return redirect("website:home")


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
    if tab not in ("profile", "orders", "addresses", "password"):
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


@login_required
def profile_password_view(request):
    redirect_url = f"{reverse('accounts:profile')}?tab=password"
    if request.method != "POST":
        return redirect(redirect_url)
    current_password = request.POST.get("current_password", "")
    new_password1 = request.POST.get("new_password1", "")
    new_password2 = request.POST.get("new_password2", "")
    if not request.user.check_password(current_password):
        messages.error(request, "Senha atual incorreta.")
        return redirect(redirect_url)
    if new_password1 != new_password2:
        messages.error(request, "As novas senhas não coincidem.")
        return redirect(redirect_url)
    try:
        validate_password(new_password1, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect(redirect_url)
    request.user.set_password(new_password1)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)
    messages.success(request, "Senha alterada com sucesso.")
    return redirect(redirect_url)


@login_required
def profile_delete_view(request):
    redirect_url = f"{reverse('accounts:profile')}?tab=password"
    if request.method != "POST":
        return redirect(redirect_url)
    if not request.user.check_password(request.POST.get("password", "")):
        messages.error(request, "Senha incorreta.")
        return redirect(redirect_url)
    open_statuses = [
        OrderStatus.NEW,
        OrderStatus.CONFIRM,
        OrderStatus.PAYMENT,
        OrderStatus.PAID,
        OrderStatus.PRODUCTION,
        OrderStatus.SENT,
    ]
    if Order.objects.filter(user=request.user, status__in=open_statuses).exists():
        messages.error(
            request,
            "Você tem pedidos em andamento. A conta só pode ser excluída "
            "após a entrega ou cancelamento de todos os pedidos.",
        )
        return redirect(redirect_url)
    user = request.user
    user.name = "Conta excluída"
    user.phone = ""
    user.cpf = ""
    user.birth_date = None
    user.email = f"excluido_{user.pk}@magno-figures.invalid"
    user.email_verified_at = None
    user.is_active = False
    user.set_unusable_password()
    user.save()
    logout(request)
    messages.success(request, "Sua conta foi excluída com sucesso.")
    return redirect("website:home")


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
