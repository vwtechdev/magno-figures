from django.conf import settings
from django.db import models

from core.models import BaseModel


class Cart(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="Usuário",
    )

    class Meta:
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Carrinho de {self.user.email}"

    @property
    def item_count(self):
        return self.items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def subtotal(self):
        items = self.items.select_related("figure").all()
        return sum(item.figure.price * item.quantity for item in items)


class CartItem(BaseModel):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Carrinho",
    )
    figure = models.ForeignKey(
        "figures.Figure",
        on_delete=models.CASCADE,
        verbose_name="Action Figure",
    )
    quantity = models.PositiveSmallIntegerField(
        default=1, verbose_name="Quantidade"
    )

    class Meta:
        verbose_name = "Item do Carrinho"
        verbose_name_plural = "Itens do Carrinho"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "figure"],
                name="unique_cart_figure",
            )
        ]

    def __str__(self):
        return f"{self.figure.name} x{self.quantity}"
