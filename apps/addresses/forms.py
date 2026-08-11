from django import forms

from apps.addresses.models import Address


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "zip_code",
            "street",
            "number",
            "complement",
            "neighborhood",
            "city",
            "state",
            "is_primary",
        ]
        widgets = {
            "zip_code": forms.TextInput(
                attrs={
                    "class": "checkout__input",
                    "inputmode": "numeric",
                    "maxlength": "9",
                    "placeholder": "00000-000",
                    "autocomplete": "postal-code",
                }
            ),
            "street": forms.TextInput(
                attrs={"class": "checkout__input", "autocomplete": "address-line1"}
            ),
            "number": forms.TextInput(
                attrs={"class": "checkout__input", "autocomplete": "address-line2"}
            ),
            "complement": forms.TextInput(
                attrs={"class": "checkout__input", "placeholder": "Apto, bloco, referência..."}
            ),
            "neighborhood": forms.TextInput(attrs={"class": "checkout__input"}),
            "city": forms.TextInput(attrs={"class": "checkout__input"}),
            "state": forms.TextInput(
                attrs={"class": "checkout__input", "maxlength": "2"}
            ),
            "is_primary": forms.CheckboxInput(),
        }
        labels = {
            "zip_code": "CEP",
            "street": "Rua",
            "number": "Número",
            "complement": "Complemento (opcional)",
            "neighborhood": "Bairro",
            "city": "Cidade",
            "state": "Estado (UF)",
            "is_primary": "Endereço principal",
        }
