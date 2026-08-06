from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from core.models import BaseModel


class CategoryManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(is_active=True)


class Category(MPTTModel, BaseModel):
    name = models.CharField(
        max_length=255, unique=True, verbose_name="Nome"
    )
    slug = models.SlugField(
        unique=True, verbose_name="Slug"
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Categoria Pai",
    )

    objects = CategoryManager()

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def figure_count(self):
        return self.figures.filter(is_active=True).count()
