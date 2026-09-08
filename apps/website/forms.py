import re

from django import forms
from django.db.models import Max

from apps.website.models import Banner, Website
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


class WebsiteAdminForm(forms.ModelForm):
    batch_upload = forms.FileField(
        label="Upload de banners",
        help_text="Selecione todas as imagens dos banners de uma vez. Máximo de 50 banners por envio.",
        required=False,
        validators=[validate_image_size, validate_image_extension],
    )

    class Meta:
        model = Website
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["batch_upload"].widget.attrs.update({"multiple": True})
        for name, field in self.fields.items():
            if name.startswith("theme_"):
                field.widget.attrs.update(
                    {
                        "data-color-field": "true",
                        "placeholder": "#RRGGBB",
                        "maxlength": "7",
                        "style": "max-width: 110px; text-transform: uppercase;",
                    }
                )

    def clean_batch_upload(self):
        uploads = self.files.getlist("batch_upload")
        validate_batch_upload_count(uploads, Banner.objects.count())
        for upload in uploads:
            validate_image_extension(upload)
            validate_image_size(upload)
        return self.cleaned_data.get("batch_upload")

    def save_banners(self, website):
        uploaded_files = self.files.getlist("batch_upload")
        if not uploaded_files:
            return
        uploaded_files.sort(key=_natural_sort_key)

        last_order = Banner.objects.aggregate(last_order=Max("order")).get("last_order") or 0
        for index, file in enumerate(uploaded_files, start=1):
            Banner.objects.create(
                website=website,
                image=file,
                order=last_order + index,
            )