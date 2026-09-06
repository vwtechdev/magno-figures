from django.contrib import admin

from apps.figures.models import Figure
from apps.newsletters.models import (
    NewsletterCampaign,
    NewsletterSubscriber,
    StockAlert,
)
from apps.newsletters.notifications import notify_stock_alerts, send_campaign


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
    fieldsets = (
        (None, {"fields": ("email", "is_active")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(NewsletterCampaign)
class NewsletterCampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_sent_display", "sent_at", "created_at")
    list_filter = ("created_at",)
    search_fields = ("subject", "message")
    readonly_fields = (
        "is_sent_display",
        "sent_at",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )
    actions = ("send_selected",)
    fieldsets = (
        (None, {"fields": ("subject", "message")}),
        ("Envio", {"fields": ("is_sent_display", "sent_at")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    @admin.display(boolean=True, description="Enviada")
    def is_sent_display(self, obj):
        return obj.is_sent

    @admin.action(description="Enviar campanha")
    def send_selected(self, request, queryset):
        total = 0
        for campaign in queryset.filter(sent_at__isnull=True):
            total += send_campaign(campaign)
        self.message_user(request, f"{total} email(s) enviado(s).")


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
