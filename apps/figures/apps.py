from django.apps import AppConfig


class FiguresConfig(AppConfig):
    name = 'apps.figures'
    verbose_name = 'Action Figures'

    def ready(self):
        from apps.figures import signals  # noqa: F401
