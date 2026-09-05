import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image

MAX_IMAGE_SIZE = 1 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def validate_batch_upload_count(uploads, existing_count=0):
    max_files = settings.DATA_UPLOAD_MAX_NUMBER_FILES
    if len(uploads) > max_files:
        raise ValidationError(
            _("Você pode enviar no máximo %(max)d arquivos por vez.")
            % {"max": max_files}
        )
    total = existing_count + len(uploads)
    if total > max_files:
        raise ValidationError(
            _(
                "Já existem %(existing)d itens e o envio em lote adicionaria mais "
                "%(batch)d, totalizando %(total)d — acima do limite de %(max)d."
            )
            % {
                "existing": existing_count,
                "batch": len(uploads),
                "total": total,
                "max": max_files,
            }
        )


def validate_image_size(image):
    if hasattr(image, "size") and image.size > MAX_IMAGE_SIZE:
        size_kb = image.size / 1024
        raise ValidationError(
            _("A imagem não pode ultrapassar 1MB. Tamanho atual: %.0fKB.") % size_kb
        )


def validate_image_extension(image):
    name = (image.name or "").lower()
    ext = os.path.splitext(name)[1]
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(_("Formato de imagem inválido. Use JPG, PNG, WebP ou GIF."))
    try:
        img = Image.open(image)
        img.verify()
    except Exception:
        raise ValidationError(_("O arquivo enviado não é uma imagem válida."))
    finally:
        image.seek(0)


def is_valid_cpf(cpf):
    """Valida um CPF pelos dígitos verificadores (aceita com/sem máscara)."""
    cpf = re.sub(r"\D", "", cpf or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for length in (9, 10):
        total = sum(int(cpf[i]) * (length + 1 - i) for i in range(length))
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if int(cpf[length]) != digit:
            return False
    return True