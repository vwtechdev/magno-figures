from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from apps.figures.models import Figure, FigureImage
from core.utils import delete_storage_file


@receiver(post_delete, sender=Figure)
def delete_figure_image(sender, instance, **kwargs):
    if instance.image:
        delete_storage_file(instance.image.storage, instance.image.name)


@receiver(post_delete, sender=FigureImage)
def delete_figure_image_file(sender, instance, **kwargs):
    if instance.image:
        delete_storage_file(instance.image.storage, instance.image.name)


def _replace_file(sender, instance, field_name, **kwargs):
    if not instance.pk:
        return
    old_name = (
        sender.objects.filter(pk=instance.pk)
        .values_list(field_name, flat=True)
        .first()
    )
    new_field = getattr(instance, field_name, None)
    new_name = getattr(new_field, "name", None) if new_field else None
    if old_name and old_name != new_name:
        storage = sender._meta.get_field(field_name).storage
        delete_storage_file(storage, old_name)


@receiver(pre_save, sender=Figure)
def replace_figure_image(sender, instance, **kwargs):
    _replace_file(sender, instance, "image")


@receiver(pre_save, sender=FigureImage)
def replace_figure_image_file(sender, instance, **kwargs):
    _replace_file(sender, instance, "image")