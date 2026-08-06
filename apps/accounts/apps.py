from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Contas de Usuários"

    def ready(self):
        import apps.accounts.signals  # noqa: F401
