from django.conf import settings
from django.db import models

from core.models import BaseModel


class AddressManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("user")


class Address(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="Usuário",
    )
    zip_code = models.CharField(
        max_length=9, verbose_name="CEP"
    )
    street = models.CharField(
        max_length=255, verbose_name="Rua"
    )
    number = models.CharField(
        max_length=20, verbose_name="Número"
    )
    complement = models.CharField(
        max_length=255, blank=True, verbose_name="Complemento"
    )
    neighborhood = models.CharField(
        max_length=255, verbose_name="Bairro"
    )
    city = models.CharField(
        max_length=255, verbose_name="Cidade"
    )
    state = models.CharField(
        max_length=2, verbose_name="Estado"
    )
    is_primary = models.BooleanField(
        default=False, verbose_name="Principal"
    )

    objects = AddressManager()

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        ordering = ["-is_primary", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user=None),
                name="address_user_not_null",
            )
        ]

    def __str__(self):
        return f"{self.street}, {self.number} - {self.city}/{self.state}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            Address.objects.filter(
                user=self.user, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        elif not Address.objects.filter(
            user=self.user, is_primary=True
        ).exclude(pk=self.pk).exists():
            self.is_primary = True
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        parts = [
            f"{self.street}, {self.number}",
            self.complement,
            f"{self.neighborhood} - {self.city}/{self.state}",
            f"CEP: {self.zip_code}",
        ]
        return "\n".join(filter(None, parts))
