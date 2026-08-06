from django.db import models

from core.models import BaseModel


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
    image = models.ImageField(
        upload_to="figures/", verbose_name="Imagem Principal"
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
    def first_image(self):
        image = self.images.order_by("order").first()
        return image.image if image else self.image


class FigureImage(BaseModel):
    figure = models.ForeignKey(
        Figure,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Action Figure",
    )
    image = models.ImageField(
        upload_to="figures/gallery/", verbose_name="Imagem"
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
