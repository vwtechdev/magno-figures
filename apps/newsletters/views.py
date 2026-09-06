from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.newsletters.models import NewsletterSubscriber, StockAlert
from apps.newsletters.notifications import parse_newsletter_token


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _safe_back(request, fallback="/"):
    referer = request.META.get("HTTP_REFERER") or fallback
    if not url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return fallback
    return referer


def subscribe_view(request):
    if request.method != "POST":
        return redirect("website:home")
    email = (request.POST.get("email") or "").strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        error = "Informe um email válido."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": error}, status=400)
        messages.error(request, error)
        return redirect(_safe_back(request))
    try:
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email
        )
    except IntegrityError:
        created = False
        subscriber = NewsletterSubscriber.objects.get(email=email)
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.save(update_fields=["is_active", "updated_by"])
        created = True
    if created:
        message = "Inscrição confirmada! Você receberá nossas novidades."
    else:
        message = "Este email já está inscrito na newsletter."
    if _is_ajax(request):
        return JsonResponse({"ok": True, "message": message})
    messages.success(request, message)
    return redirect(_safe_back(request))


def unsubscribe_view(request, token):
    try:
        data = parse_newsletter_token(token)
    except signing.BadSignature:
        return render(
            request, "newsletters/unsubscribe.html", {"valid": False}, status=400
        )
    NewsletterSubscriber.objects.filter(email=data.get("email")).update(
        is_active=False
    )
    return render(
        request,
        "newsletters/unsubscribe.html",
        {"valid": True, "email": data.get("email")},
    )


def stock_alert_unsubscribe_view(request, token):
    from apps.newsletters.notifications import parse_stock_alert_token

    try:
        data = parse_stock_alert_token(token)
    except signing.BadSignature:
        return render(
            request, "newsletters/unsubscribe.html", {"valid": False}, status=400
        )
    StockAlert.objects.filter(
        figure_id=data.get("figure_id"), email=data.get("email")
    ).delete()
    return render(
        request,
        "newsletters/unsubscribe.html",
        {"valid": True, "email": data.get("email")},
    )
