from django.contrib import admin

from apps.figures.models import Figure, FigureImage


class FigureImageInline(admin.TabularInline):
    model = FigureImage
    extra = 1
    fields = ("image", "order")
    ordering = ("order",)


@admin.register(Figure)
class FigureAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "in_stock", "is_active", "created_at")
    list_filter = ("is_active", "categories", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("categories",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    inlines = [FigureImageInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "price", "stock")}),
        ("Imagens", {"fields": ("image",)}),
        ("Categorias", {"fields": ("categories",)}),
        ("Status", {"fields": ("is_active",)}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(FigureImage)
class FigureImageAdmin(admin.ModelAdmin):
    list_display = ("figure", "order")
    list_filter = ("figure",)
    ordering = ("figure", "order")
