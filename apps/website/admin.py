from django.contrib import admin

from apps.website.models import Website


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ("company_name", "whatsapp", "email")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identidade", {"fields": ("company_name", "logo", "favicon")}),
        ("Contato", {"fields": ("whatsapp", "email", "instagram", "facebook")}),
        ("Conteúdo", {"fields": ("about", "privacy_policy", "terms")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    def has_add_permission(self, request):
        if Website.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False
