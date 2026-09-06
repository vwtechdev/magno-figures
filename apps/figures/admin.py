from django.contrib import admin
from django.template.loader import get_template

from apps.figures.forms import FigureAdminForm
from apps.figures.models import Figure, FigureImage, StockAlert
from apps.figures.notifications import notify_stock_alerts


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
    list_display = ("name", "price", "stock", "sold_out", "is_nsfw_display", "pending_alerts_display", "is_active", "created_at")
    list_filter = ("is_active", "categories", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("categories",)
    readonly_fields = ("is_nsfw_display", "pending_alerts_display", "created_at", "updated_at", "created_by", "updated_by")
    inlines = [FigureImageInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "image", "batch_upload", "price", "stock")}),
        ("Envio", {"fields": ("weight_kg", "height_cm", "width_cm", "length_cm")}),
        ("Categorias", {"fields": ("categories",)}),
        ("Status", {"fields": ("is_active", "sold_out", "is_nsfw_display", "pending_alerts_display")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    @admin.display(boolean=True, description="+18")
    def is_nsfw_display(self, obj):
        return obj.is_nsfw

    @admin.display(description="Avisos pendentes")
    def pending_alerts_display(self, obj):
        return obj.stock_alerts.filter(is_notified=False).count()


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("email", "figure", "is_notified", "created_at")
    list_filter = ("is_notified", "created_at")
    search_fields = ("email", "figure__name")
    autocomplete_fields = ("figure",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    actions = ("resend_notification",)
    fieldsets = (
        (None, {"fields": ("figure", "email", "is_notified")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    @admin.action(description="Enviar aviso de disponibilidade")
    def resend_notification(self, request, queryset):
        figure_ids = (
            queryset.filter(is_notified=False)
            .values_list("figure_id", flat=True)
            .distinct()
        )
        total = 0
        for figure in Figure.objects.filter(pk__in=figure_ids):
            total += notify_stock_alerts(figure)
        self.message_user(request, f"{total} aviso(s) enviado(s).")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.save_gallery(form.instance)
