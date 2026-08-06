from django.core.cache import cache
from django.db import models

from core.models import BaseModel


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
        max_length=255, verbose_name="Nome da Empresa"
    )
    logo = models.ImageField(
        upload_to="website/", verbose_name="Logo"
    )
    favicon = models.ImageField(
        upload_to="website/", verbose_name="Favicon"
    )
    whatsapp = models.CharField(
        max_length=20, verbose_name="WhatsApp"
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

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        Website.objects.clear_cache()

    @property
    def whatsapp_link(self):
        number = "".join(filter(str.isdigit, self.whatsapp))
        return f"https://wa.me/55{number}" if number else "#"

    @property
    def whatsapp_api_link(self):
        number = "".join(filter(str.isdigit, self.whatsapp))
        return f"https://api.whatsapp.com/send?phone=55{number}" if number else "#"
