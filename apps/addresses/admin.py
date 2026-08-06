from django.contrib import admin

from apps.addresses.models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "street", "number", "city", "state", "is_primary")
    list_filter = ("is_primary", "state", "city")
    search_fields = ("user__email", "street", "city", "zip_code")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Usuário", {"fields": ("user",)}),
        (
            "Endereço",
            {
                "fields": (
                    "zip_code",
                    "street",
                    "number",
                    "complement",
                    "neighborhood",
                    "city",
                    "state",
                )
            },
        ),
        ("Status", {"fields": ("is_primary", "is_active")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )
