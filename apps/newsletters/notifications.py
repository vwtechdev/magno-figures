from django.core import signing
from django.urls import reverse

from core.mail import send_mail_async
from core.utils import site_base_url

STOCK_ALERT_SALT = "stock-alert-unsubscribe"
NEWSLETTER_SALT = "newsletter-unsubscribe"


def stock_alert_token(alert):
    return signing.dumps(
        {"figure_id": alert.figure_id, "email": alert.email},
        salt=STOCK_ALERT_SALT,
    )


def parse_stock_alert_token(token):
    return signing.loads(token, salt=STOCK_ALERT_SALT)


def newsletter_token(subscriber):
    email = getattr(subscriber, "email", subscriber)
    return signing.dumps({"email": email}, salt=NEWSLETTER_SALT)


def parse_newsletter_token(token):
    return signing.loads(token, salt=NEWSLETTER_SALT)


def format_price(value):
    return f"{value:.2f}".replace(".", ",")


def notify_stock_alerts(figure):
    from apps.newsletters.models import StockAlert

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
            "newsletters:stock_alert_unsubscribe",
            args=[stock_alert_token(alert)],
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


def send_campaign(campaign):
    from django.utils import timezone

    from apps.newsletters.models import NewsletterSubscriber

    if campaign.is_sent:
        return 0
    subscribers = list(
        NewsletterSubscriber.objects.filter(is_active=True)
    )
    base = site_base_url()
    for subscriber in subscribers:
        unsubscribe_url = base + reverse(
            "newsletters:unsubscribe",
            args=[newsletter_token(subscriber)],
        )
        message = (
            f"{campaign.message}\n\n"
            "---\n"
            "Não quer mais receber nossas novidades? "
            f"Cancele aqui: {unsubscribe_url}"
        )
        send_mail_async(campaign.subject, message, [subscriber.email])
    campaign.sent_at = timezone.now()
    campaign.save(update_fields=["sent_at", "updated_by"])
    return len(subscribers)
