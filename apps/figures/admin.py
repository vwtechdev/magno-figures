from django.contrib import admin
from django.template.loader import get_template

from apps.figures.forms import FigureAdminForm
from apps.figures.models import Figure, FigureImage


class FigureImageInline(admin.TabularInline):
    model = FigureImage
    fields = ("order", "image_thumbnail")
    readonly_fields = ("image_thumbnail",)
    ordering = ["order"]
    max_num = 0
    extra = 0
    can_delete = True
    verbose_name = "Imagem da galeria"
    verbose_name_plural = "Imagens da galeria"

    def image_thumbnail(self, instance):
        tpl = get_template("admin/thumbnail.html")
        return tpl.render({"item": instance})

    image_thumbnail.short_description = "Miniatura"


@admin.register(Figure)
class FigureAdmin(admin.ModelAdmin):
    form = FigureAdminForm
    list_display = ("name", "price", "stock", "sold_out", "is_active", "created_at")
    list_filter = ("is_active", "categories", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("categories",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    inlines = [FigureImageInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "image", "batch_upload", "price", "stock")}),
        ("Envio", {"fields": ("weight_kg", "height_cm", "width_cm", "length_cm")}),
        ("Categorias", {"fields": ("categories",)}),
        ("Status", {"fields": ("is_active", "sold_out")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.save_gallery(form.instance)
