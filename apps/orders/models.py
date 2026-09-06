from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from core.models import BaseModel


class OrderStatus(models.TextChoices):
    NEW = "NEW", "Novo Pedido"
    CONFIRM = "CONFIRM", "Aguardando Confirmação"
    PAYMENT = "PAYMENT", "Aguardando Pagamento"
    PAID = "PAID", "Pedido Pago"
    PRODUCTION = "PRODUCTION", "Em Produção"
    SENT = "SENT", "Pedido Enviado"
    CANCELED = "CANCELED", "Pedido Cancelado"
    DELIVERED = "DELIVERED", "Pedido Entregue"


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
    shipping_service = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Serviço de Envio",
    )
    shipping_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valor do Frete",
    )
    tracking_code = models.CharField(
        max_length=60, blank=True, verbose_name="Código de Rastreio"
    )

    objects = OrderManager()

    TRACKING_PORTALS = {
        "correios": "https://rastreamento.correios.com.br/",
        "jadlog": "https://www.jadlog.com.br/jadlog/rastreie",
        "loggi": "https://www.loggi.com/rastreador/",
    }

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pedido #{self.pk}"

    def clean(self):
        super().clean()
        if self.status == OrderStatus.SENT and not self.tracking_code.strip():
            raise ValidationError(
                {
                    "tracking_code": (
                        "Informe o código de rastreio para marcar "
                        "o pedido como enviado."
                    )
                }
            )

    @property
    def tracking_url(self):
        if not self.tracking_code.strip():
            return None
        service = (self.shipping_service or "").lower()
        if "jadlog" in service:
            return self.TRACKING_PORTALS["jadlog"]
        if "loggi" in service:
            return self.TRACKING_PORTALS["loggi"]
        if any(key in service for key in ("pac", "sedex", "mini", "correios")):
            return self.TRACKING_PORTALS["correios"]
        return None

    @property
    def total(self):
        return self.items.aggregate(
            total=Sum(models.F("price") * models.F("quantity"))
        )["total"] or 0.0

    @property
    def total_with_shipping(self):
        return self.total + (self.shipping_price or 0)

    @property
    def item_count(self):
        return self.items.aggregate(total=Sum("quantity"))["total"] or 0

    @property
    def user_status(self):
        if self.status == OrderStatus.NEW:
            return "confirm"
        return self.status.lower()

    @property
    def user_status_display(self):
        if self.status == OrderStatus.NEW:
            return "Aguardando Confirmação"
        return self.get_status_display()

    @property
    def can_cancel(self):
        return self.status not in {
            OrderStatus.PAID,
            OrderStatus.PRODUCTION,
            OrderStatus.SENT,
            OrderStatus.CANCELED,
            OrderStatus.DELIVERED,
        }

    def _items_text(self):
        return "".join(
            f"* {item.quantity}x {item.figure.name} — R$ {item.price:.2f}\n"
            for item in self.items.select_related("figure").all()
        )

    def generate_whatsapp_message(self):
        lines = [
            "Olá!",
            "",
            f"*Novo Pedido #{self.pk}*",
            "",
            f"*Cliente:* {self.user.name}",
            f"*Telefone:* {self.user.phone}",
        ]
        if self.user.cpf:
            lines.append(f"*CPF:* {self.user.cpf}")
        lines += [
            "",
            "*Itens:*",
            self._items_text(),
            "*Endereço:*",
            self.address.full_address,
            "",
        ]
        subtotal = self.total
        if self.shipping_service and self.shipping_price is not None:
            lines += [
                f"*Subtotal:* R$ {subtotal:.2f}",
                f"*Frete:* R$ {self.shipping_price:.2f} ({self.shipping_service})",
                f"*Total:* R$ {subtotal + self.shipping_price:.2f}",
            ]
        else:
            lines.append(f"*Total:* R$ {subtotal:.2f}")
        lines += ["", "Gostaria de finalizar este pedido?"]
        return "\n".join(lines)

    def generate_confirmation_message(self):
        message = (
            f"Olá, {self.user.name}!\n\n"
            f"Recebemos seu pedido *#{self.pk}* na Magno Figures:\n\n"
            f"*Itens:*\n"
            f"{self._items_text()}\n"
            f"*Endereço de entrega:*\n"
            f"{self.address.full_address}\n\n"
            f"*Total:* R$ {self.total:.2f}\n\n"
            f"Confirma a realização desse pedido? Assim que você confirmar, "
            f"envio os dados para o pagamento."
        )
        return message

    def _whatsapp_url(self, message):
        from apps.website.models import Website

        config = Website.objects.get_config()
        return f"{config.whatsapp_api_link}&text={quote(message)}"

    def get_whatsapp_url(self):
        return self._whatsapp_url(self.generate_whatsapp_message())

    def get_confirmation_url(self):
        return self._whatsapp_url(self.generate_confirmation_message())


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
