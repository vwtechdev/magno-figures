from django.core import signing
from django.urls import reverse

from core.mail import send_mail_async
from core.utils import site_base_url

UNSUBSCRIBE_SALT = "stock-alert-unsubscribe"


def stock_alert_token(alert):
    return signing.dumps(
        {"figure_id": alert.figure_id, "email": alert.email},
        salt=UNSUBSCRIBE_SALT,
    )


def parse_stock_alert_token(token):
    return signing.loads(token, salt=UNSUBSCRIBE_SALT)


def format_price(value):
    return f"{value:.2f}".replace(".", ",")


def notify_stock_alerts(figure):
    from apps.figures.models import StockAlert

    pending = list(
        StockAlert.objects.filter(
            figure=figure, figure__is_active=True, is_notified=False
        )
    )
    if not pending:
        return 0
    base = site_base_url()
    product_url = base + reverse("figures:detail", args=[figure.slug])
    for alert in pending:
        unsubscribe_url = base + reverse(
            "figures:unsubscribe", args=[stock_alert_token(alert)]
        )
        subject = f"{figure.name} está disponível!"
        message = (
            "Olá!\n\n"
            f"O item {figure.name} está disponível na Magno Figures "
            f"por R$ {format_price(figure.price)}.\n\n"
            f"Garanta o seu: {product_url}\n\n"
            "Não quer mais receber estes avisos? "
            f"Cancele aqui: {unsubscribe_url}"
        )
        send_mail_async(subject, message, [alert.email])
        alert.is_notified = True
        alert.save(update_fields=["is_notified", "updated_by"])
    return len(pending)
