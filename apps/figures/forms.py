import re

from django import forms
from django.db.models import Max

from apps.figures.models import Figure, FigureImage
from core.validators import (
    validate_batch_upload_count,
    validate_image_extension,
    validate_image_size,
)


def _natural_sort_key(file):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", file.name)
    ]


class FigureAdminForm(forms.ModelForm):
    batch_upload = forms.FileField(
        label="Upload em lote",
        help_text="Selecione todas as imagens da galeria da figura de uma vez. Máximo de 50 imagens por figura.",
        required=False,
        validators=[validate_image_size, validate_image_extension],
    )

    class Meta:
        model = Figure
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["batch_upload"].widget.attrs.update({"multiple": True})

    def clean_batch_upload(self):
        uploads = self.files.getlist("batch_upload")
        existing = (
            FigureImage.objects.filter(figure=self.instance).count()
            if self.instance.pk
            else 0
        )
        validate_batch_upload_count(uploads, existing)
        for upload in uploads:
            validate_image_extension(upload)
            validate_image_size(upload)
        return self.cleaned_data.get("batch_upload")

    def save_gallery(self, figure):
        uploaded_files = self.files.getlist("batch_upload")
        if not uploaded_files:
            return
        uploaded_files.sort(key=_natural_sort_key)
        last_order = (
            FigureImage.objects.filter(figure=figure)
            .aggregate(last_order=Max("order"))
            .get("last_order")
            or 0
        )

        for index, file in enumerate(uploaded_files, start=1):
            FigureImage.objects.create(
                figure=figure,
                image=file,
                order=last_order + index,
            )