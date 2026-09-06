from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"
        widgets = {
            "phone": forms.TextInput(
                attrs={"data-phone-mask": "true"}
            ),
        }


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    list_display = ("email", "name", "phone", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados Pessoais", {"fields": ("name", "phone", "cpf", "birth_date")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    class Media:
        js = ("js/accounts/phone-mask.js",)
