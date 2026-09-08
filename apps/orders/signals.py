from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.orders.models import Order, OrderStatus
from core.mail import send_mail_async


@receiver(pre_save, sender=Order)
def stash_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._was_status = None
        return
    instance._was_status = (
        sender.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender=Order)
def notify_tracking_code_on_shipment(sender, instance, created, **kwargs):
    if created:
        return
    if (
        getattr(instance, "_was_status", None) == OrderStatus.SENT
        or instance.status != OrderStatus.SENT
    ):
        return
    if not instance.tracking_code.strip() or not instance.user.email:
        return
    name = instance.user.name
    email = instance.user.email
    order_pk = instance.pk
    tracking_code = instance.tracking_code.strip()
    tracking_url = instance.tracking_url
    lines = [
        f"Olá, {name}!",
        "",
        f"Seu pedido #{order_pk} foi enviado!",
        "",
        f"Código de rastreio: {tracking_code}",
    ]
    if tracking_url:
        lines += [
            "",
            f"Acompanhe aqui: {tracking_url}",
        ]

    def _dispatch():
        send_mail_async(
            f"Seu pedido #{order_pk} foi enviado!",
            "\n".join(lines),
            [email],
        )

    transaction.on_commit(_dispatch)
