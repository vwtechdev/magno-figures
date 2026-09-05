from django.conf import settings


def site_base_url():
    """URL base absoluta do site (scheme + domínio), derivada de settings.DOMAIN."""
    domain = settings.DOMAIN
    if domain.startswith(("localhost", "127.")):
        return f"http://{domain}"
    return f"https://{domain}"


def delete_storage_file(storage, name):
    """Apaga um arquivo do storage se existir (não falha se ausente)."""
    if name and storage.exists(name):
        storage.delete(name)