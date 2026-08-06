from urllib.parse import quote

from django.conf import settings
from django.db import models
from django.db.models import Sum

from core.models import BaseModel


class OrderStatus(models.TextChoices):
    NEW = "NEW", "Novo"
    WHATSAPP_SENT = "WHATSAPP_SENT", "Enviado WhatsApp"
    NEGOTIATING = "NEGOTIATING", "Em Negociação"
    PAID = "PAID", "Pago"
    CANCELLED = "CANCELLED", "Cancelado"
    COMPLETED = "COMPLETED", "Finalizado"


class OrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("user", "address")


class Order(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Usuário",
    )
    address = models.ForeignKey(
        "addresses.Address",
        on_delete=models.PROTECT,
        verbose_name="Endereço de Entrega",
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.NEW,
        db_index=True,
        verbose_name="Status",
    )

    objects = OrderManager()

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pedido #{self.pk}"

    @property
    def total(self):
        return self.items.aggregate(
            total=Sum(models.F("price") * models.F("quantity"))
        )["total"] or 0.0

    @property
    def item_count(self):
        return self.items.aggregate(total=Sum("quantity"))["total"] or 0

    def generate_whatsapp_message(self):
        items_text = ""
        for item in self.items.select_related("figure").all():
            items_text += f"* {item.quantity}x {item.figure.name} — R$ {item.price:.2f}\n"

        message = (
            f"Olá! 🎯\n\n"
            f"*Novo Pedido #{self.pk}*\n\n"
            f"*Cliente:* {self.user.name}\n"
            f"*Telefone:* {self.user.phone}\n\n"
            f"*Itens:*\n"
            f"{items_text}\n"
            f"*Endereço:*\n"
            f"{self.address.full_address}\n\n"
            f"*Total:* R$ {self.total:.2f}\n\n"
            f"Gostaria de finalizar este pedido?"
        )
        return message

    def get_whatsapp_url(self):
        from apps.website.models import Website

        config = Website.objects.get_config()
        message = self.generate_whatsapp_message()
        whatsapp_link = config.whatsapp_api_link
        return f"{whatsapp_link}&text={quote(message)}"


class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Pedido",
    )
    figure = models.ForeignKey(
        "figures.Figure",
        on_delete=models.PROTECT,
        verbose_name="Action Figure",
    )
    quantity = models.PositiveSmallIntegerField(
        verbose_name="Quantidade"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço Unitário",
    )

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.figure.name} x{self.quantity} — R$ {self.price:.2f}"
