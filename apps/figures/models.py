from django.db import models

from core.models import BaseModel
from core.validators import validate_image_size


class FigureManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(is_active=True)

    def available(self):
        return self.active().filter(stock__gt=0)


class Figure(BaseModel):
    name = models.CharField(
        max_length=255, verbose_name="Nome"
    )
    slug = models.SlugField(
        unique=True, verbose_name="Slug"
    )
    description = models.TextField(
        verbose_name="Descrição"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Preço"
    )
    stock = models.PositiveIntegerField(
        default=0, verbose_name="Estoque"
    )
    sold_out = models.BooleanField(
        default=False, verbose_name="Esgotado"
    )
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=3,
        verbose_name="Peso (kg)",
    )
    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=60,
        verbose_name="Altura (cm)",
    )
    width_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=40,
        verbose_name="Largura (cm)",
    )
    length_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=35,
        verbose_name="Comprimento (cm)",
    )
    image = models.ImageField(
        upload_to="figures/",
        validators=[validate_image_size],
        verbose_name="Imagem Principal",
    )
    categories = models.ManyToManyField(
        "categories.Category",
        related_name="figures",
        verbose_name="Categorias",
    )

    objects = FigureManager()

    class Meta:
        verbose_name = "Action Figure"
        verbose_name_plural = "Action Figures"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def stock_status(self):
        if self.sold_out:
            return "sold"
        if self.in_stock:
            return "in"
        return "preorder"

    @property
    def first_image(self):
        if self.image:
            return self.image
        image = self.images.order_by("order").first()
        return image.image if image else None


class FigureImage(BaseModel):
    figure = models.ForeignKey(
        Figure,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Action Figure",
    )
    image = models.ImageField(
        upload_to="figures/gallery/",
        validators=[validate_image_size],
        verbose_name="Imagem",
    )
    order = models.PositiveSmallIntegerField(
        default=0, verbose_name="Ordem"
    )

    class Meta:
        verbose_name = "Imagem"
        verbose_name_plural = "Imagens"
        ordering = ["order"]

    def __str__(self):
        return f"Imagem {self.order} - {self.figure.name}"
