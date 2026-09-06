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
    lines = [
        f"Olá, {instance.user.name}!",
        "",
        f"Seu pedido #{instance.pk} foi enviado!",
        "",
        f"Código de rastreio: {instance.tracking_code.strip()}",
    ]
    if instance.tracking_url:
        lines += [
            "",
            f"Acompanhe aqui: {instance.tracking_url}",
        ]
    send_mail_async(
        f"Seu pedido #{instance.pk} foi enviado!",
        "\n".join(lines),
        [instance.user.email],
    )
