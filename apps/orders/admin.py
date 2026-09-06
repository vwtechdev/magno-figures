from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils.html import format_html

from apps.orders.models import Order, OrderItem, OrderStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("figure", "quantity", "price")
    readonly_fields = ("figure", "quantity", "price")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_form_template = "admin/orders/order/change_form.html"
    list_display = ("pk", "user", "status", "tracking_code", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__name", "pk", "tracking_code")
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "user",
        "address",
        "whatsapp_link",
    )
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {"fields": ("user", "address", "whatsapp_link", "status", "tracking_code")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    def whatsapp_link(self, obj):
        if obj and obj.pk:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">Enviar mensagem no WhatsApp</a>',
                obj.get_confirmation_url(),
            )
        return "-"

    whatsapp_link.short_description = "Mensagem de pedido"
    whatsapp_link.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/send-confirmation/",
                self.admin_site.admin_view(self.send_confirmation_view),
                name="orders_order_send_confirmation",
            ),
            path(
                "<int:pk>/send-production/",
                self.admin_site.admin_view(self.send_production_view),
                name="orders_order_send_production",
            ),
            path(
                "<int:pk>/send-shipment/",
                self.admin_site.admin_view(self.send_shipment_view),
                name="orders_order_send_shipment",
            ),
        ]
        return custom + urls

    def _transition_and_redirect(self, request, pk, status, url_getter):
        change_url = redirect("admin:orders_order_change", pk)
        if request.method != "POST":
            return change_url
        order = get_object_or_404(Order, pk=pk)
        order.status = status
        try:
            order.clean()
        except ValidationError as exc:
            for field_errors in exc.message_dict.values():
                for error in field_errors:
                    messages.error(request, error)
            return change_url
        order.updated_by = request.user
        order.save(update_fields=["status", "updated_by"])
        return redirect(url_getter(order))

    def send_confirmation_view(self, request, pk):
        return self._transition_and_redirect(
            request, pk, OrderStatus.CONFIRM, Order.get_confirmation_url
        )

    def send_production_view(self, request, pk):
        return self._transition_and_redirect(
            request, pk, OrderStatus.PRODUCTION, Order.get_production_url
        )

    def send_shipment_view(self, request, pk):
        return self._transition_and_redirect(
            request, pk, OrderStatus.SENT, Order.get_shipment_url
        )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "figure", "quantity", "price")
    list_filter = ("order__status",)
    search_fields = ("figure__name", "order__pk")
    readonly_fields = ("figure", "quantity", "price", "order")
