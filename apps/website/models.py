from django.core.cache import cache
from django.db import models

from core.models import BaseModel
from core.validators import validate_image_size


class BannerManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(is_active=True)


class Banner(BaseModel):
    website = models.ForeignKey(
        "website.Website",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="banners",
        verbose_name="Website",
    )
    title = models.CharField(
        max_length=255, blank=True, verbose_name="Título"
    )
    subtitle = models.CharField(
        max_length=255, blank=True, verbose_name="Subtítulo"
    )
    image = models.ImageField(
        upload_to="website/banners/",
        validators=[validate_image_size],
        verbose_name="Imagem",
    )
    link = models.URLField(
        blank=True, verbose_name="Link"
    )
    order = models.PositiveSmallIntegerField(
        default=0, verbose_name="Ordem"
    )

    objects = BannerManager()

    class Meta:
        verbose_name = "Banner do Site"
        verbose_name_plural = "Banners do Site"
        ordering = ["order"]

    def __str__(self):
        return self.title or f"Banner {self.pk}"


class WebsiteManager(models.Manager):
    def get_config(self):
        cache_key = "website_config"
        config = cache.get(cache_key)
        if config is None:
            config, _ = self.get_queryset().get_or_create(
                pk=1,
                defaults={
                    "company_name": "Magno Figures",
                    "whatsapp": "",
                    "description": "",
                    "origin_zip_code": "",
                    "about": "",
                    "privacy_policy": "",
                },
            )
            cache.set(cache_key, config, timeout=3600)
        return config

    def clear_cache(self):
        cache.delete("website_config")


class Website(BaseModel):
    company_name = models.CharField(
        max_length=255, verbose_name="Título do Site"
    )
    logo = models.ImageField(
        upload_to="website/",
        validators=[validate_image_size],
        verbose_name="Logo",
    )
    favicon = models.ImageField(
        upload_to="website/",
        validators=[validate_image_size],
        verbose_name="Favicon",
    )
    whatsapp = models.CharField(
        max_length=20, verbose_name="WhatsApp"
    )
    description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="Descrição (SEO)",
        help_text="Texto curto usado no footer e como meta description nas buscas do Google (máx. 160 caracteres).",
    )
    origin_zip_code = models.CharField(
        max_length=9,
        blank=True,
        verbose_name="CEP de Origem",
        help_text="CEP de onde as encomendas são postadas (usado no cálculo de frete).",
    )
    instagram = models.URLField(
        blank=True, verbose_name="Instagram"
    )
    facebook = models.URLField(
        blank=True, verbose_name="Facebook"
    )
    email = models.EmailField(
        blank=True, verbose_name="Email"
    )
    about = models.TextField(
        verbose_name="Sobre"
    )
    privacy_policy = models.TextField(
        verbose_name="Política de Privacidade"
    )
    terms = models.TextField(
        blank=True, verbose_name="Termos de Uso"
    )

    objects = WebsiteManager()

    class Meta:
        verbose_name = "Configuração do Site"
        verbose_name_plural = "Configurações do Site"

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        Website.objects.clear_cache()

    def _clean_whatsapp_number(self):
        number = "".join(filter(str.isdigit, self.whatsapp))
        if number and not number.startswith("55"):
            number = f"55{number}"
        return number

    @property
    def whatsapp_link(self):
        number = self._clean_whatsapp_number()
        return f"https://wa.me/{number}" if number else "#"

    @property
    def whatsapp_api_link(self):
        number = self._clean_whatsapp_number()
        return f"https://api.whatsapp.com/send?phone={number}" if number else "#"
