from django.contrib import admin
from django.template.loader import get_template

from apps.website.forms import WebsiteAdminForm
from apps.website.models import Banner, Website


class BannerInline(admin.TabularInline):
    model = Banner
    fields = ("title", "subtitle", "link", "order", "image_thumbnail")
    readonly_fields = ("image_thumbnail",)
    ordering = ["order"]
    max_num = 0
    extra = 0
    can_delete = True
    verbose_name = "Banner"
    verbose_name_plural = "Banners"

    def image_thumbnail(self, instance):
        tpl = get_template("admin/thumbnail.html")
        return tpl.render({"item": instance})

    image_thumbnail.short_description = "Miniatura"


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    form = WebsiteAdminForm
    inlines = [BannerInline]
    list_display = ("company_name", "whatsapp", "email")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        ("Identidade", {"fields": ("company_name", "description", "logo", "favicon", "batch_upload")}),
        ("Contato", {"fields": ("whatsapp", "email", "instagram", "facebook")}),
        ("Envio", {"fields": ("origin_zip_code",)}),
        ("Sobre", {"fields": ("about", "privacy_policy", "terms")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.save_banners(form.instance)

    def has_add_permission(self, request):
        if Website.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False
