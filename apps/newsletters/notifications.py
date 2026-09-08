from django.core import signing
from django.db import transaction
from django.urls import reverse

from core.mail import dispatch_email_batch
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
    payloads = []
    alert_ids = []
    for alert in pending:
        unsubscribe_url = base + reverse(
            "newsletters:stock_alert_unsubscribe",
            args=[stock_alert_token(alert)],
        )
        subject = f"{figure.name} está disponível!"
        message = (
            "Olá!\n\n"
            f"O item {figure.name} está disponível na Magno Figures "
            f"por R$ {format_price(figure.sale_price)}.\n\n"
            f"Garanta o seu: {product_url}\n\n"
            "Não quer mais receber estes avisos? "
            f"Cancele aqui: {unsubscribe_url}"
        )
        payloads.append(
            {"subject": subject, "message": message, "recipients": [alert.email]}
        )
        alert_ids.append(alert.pk)

    def _mark_notified(results):
        succeeded = [
            alert_id for alert_id, ok in zip(alert_ids, results) if ok
        ]
        if succeeded:
            StockAlert.objects.filter(
                pk__in=succeeded, is_notified=False
            ).update(is_notified=True)

    def _dispatch():
        dispatch_email_batch(payloads, on_success=_mark_notified)

    transaction.on_commit(_dispatch)
    return len(pending)


def send_campaign(campaign):
    from django.utils import timezone

    from apps.newsletters.models import NewsletterCampaign, NewsletterSubscriber

    if campaign.is_sent:
        return 0
    subscribers = list(
        NewsletterSubscriber.objects.filter(is_active=True)
    )
    base = site_base_url()
    payloads = []
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
        payloads.append(
            {
                "subject": campaign.subject,
                "message": message,
                "recipients": [subscriber.email],
            }
        )
    campaign_pk = campaign.pk

    def _mark_sent(results):
        # Envio total ou nada: se algum falhar, a campanha continua
        # como não enviada para permitir nova tentativa pelo admin.
        if results and all(results):
            NewsletterCampaign.objects.filter(
                pk=campaign_pk, sent_at__isnull=True
            ).update(sent_at=timezone.now())

    def _dispatch():
        dispatch_email_batch(payloads, on_success=_mark_sent)

    transaction.on_commit(_dispatch)
    return len(subscribers)
