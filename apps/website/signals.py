from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from apps.website.models import Banner, Website
from core.utils import delete_storage_file


@receiver(post_delete, sender=Banner)
def delete_banner_image(sender, instance, **kwargs):
    if instance.image:
        delete_storage_file(instance.image.storage, instance.image.name)


@receiver(pre_save, sender=Banner)
def replace_banner_image(sender, instance, **kwargs):
    if not instance.pk:
        return
    old_name = (
        sender.objects.filter(pk=instance.pk)
        .values_list("image", flat=True)
        .first()
    )
    new_field = getattr(instance, "image", None)
    new_name = getattr(new_field, "name", None) if new_field else None
    if old_name and old_name != new_name:
        storage = sender._meta.get_field("image").storage
        delete_storage_file(storage, old_name)


@receiver(post_delete, sender=Website)
def delete_website_files(sender, instance, **kwargs):
    for field_name in ("logo", "favicon"):
        field = getattr(instance, field_name, None)
        if field:
            delete_storage_file(field.storage, field.name)


@receiver(pre_save, sender=Website)
def replace_website_files(sender, instance, **kwargs):
    if not instance.pk:
        return
    current = (
        sender.objects.filter(pk=instance.pk)
        .values_list("logo", "favicon")
        .first()
    )
    if not current:
        return
    for field_name, old_name in zip(("logo", "favicon"), current):
        new_field = getattr(instance, field_name, None)
        new_name = getattr(new_field, "name", None) if new_field else None
        if old_name and old_name != new_name:
            storage = sender._meta.get_field(field_name).storage
            delete_storage_file(storage, old_name)