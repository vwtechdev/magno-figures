from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = 'apps.website'
    verbose_name = 'Configurações do Site'

    def ready(self):
        from apps.website import signals  # noqa: F401
