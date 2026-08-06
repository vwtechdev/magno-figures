from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        (None, {"fields": ("name", "slug", "parent")}),
        ("Status", {"fields": ("is_active",)}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )
