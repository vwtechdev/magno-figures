from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
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
    list_display = ("pk", "user", "status", "tracking_code", "subtotal_display", "shipping_display", "grand_total_display", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__name", "pk", "tracking_code")
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "user",
        "address",
        "status_display",
        "subtotal_display",
        "shipping_display",
        "grand_total_display",
    )
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {"fields": ("user", "address", "status_display", "tracking_code")}),
        ("Totais", {"fields": ("subtotal_display", "shipping_display", "grand_total_display")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

    STATUS_BADGE_CLASSES = {
        OrderStatus.NEW: "st-new",
        OrderStatus.CONFIRM: "st-confirm",
        OrderStatus.PAYMENT: "st-payment",
        OrderStatus.PAID: "st-paid",
        OrderStatus.PRODUCTION: "st-production",
        OrderStatus.SENT: "st-sent",
        OrderStatus.CANCELED: "st-canceled",
        OrderStatus.DELIVERED: "st-delivered",
    }

    @admin.display(description="Status")
    def status_display(self, obj):
        if not obj or not obj.pk:
            return "-"
        badge_class = self.STATUS_BADGE_CLASSES.get(obj.status, "st-new")
        return format_html(
            '<span id="order-status" class="mf-status-badge {}">{}</span>',
            badge_class,
            obj.get_status_display(),
        )

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        if obj and obj.pk:
            return f"R$ {obj.total:.2f}".replace(".", ",")
        return "-"

    @admin.display(description="Frete")
    def shipping_display(self, obj):
        if obj and obj.pk and obj.shipping_price is not None:
            service = f" ({obj.shipping_service})" if obj.shipping_service else ""
            return f"R$ {obj.shipping_price:.2f}{service}".replace(".", ",")
        return "A combinar"

    @admin.display(description="Total")
    def grand_total_display(self, obj):
        if obj and obj.pk:
            return f"R$ {obj.total_with_shipping:.2f}".replace(".", ",")
        return "-"

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
            path(
                "<int:pk>/send-payment/",
                self.admin_site.admin_view(self.send_payment_view),
                name="orders_order_send_payment",
            ),
            path(
                "<int:pk>/send-paid/",
                self.admin_site.admin_view(self.send_paid_view),
                name="orders_order_send_paid",
            ),
            path(
                "<int:pk>/send-delivered/",
                self.admin_site.admin_view(self.send_delivered_view),
                name="orders_order_send_delivered",
            ),
            path(
                "<int:pk>/send-canceled/",
                self.admin_site.admin_view(self.send_canceled_view),
                name="orders_order_send_canceled",
            ),
        ]
        return custom + urls

    def _transition_result(self, request, pk, status, url_getter=None):
        if request.method != "POST":
            return JsonResponse({"error": "Método não permitido."}, status=405)
        order = get_object_or_404(Order, pk=pk)
        order.status = status
        try:
            order.clean()
        except ValidationError as exc:
            errors = [
                str(error)
                for field_errors in exc.message_dict.values()
                for error in field_errors
            ]
            messages.error(request, " ".join(errors))
            return JsonResponse({"error": " ".join(errors)}, status=400)
        order.updated_by = request.user
        order.save(update_fields=["status", "updated_by"])
        payload = {
            "status_display": order.get_status_display(),
            "badge_class": self.STATUS_BADGE_CLASSES.get(
                order.status, "st-new"
            ),
        }
        if url_getter:
            payload["url"] = url_getter(order)
        else:
            payload["ok"] = True
        return JsonResponse(payload)

    def send_confirmation_view(self, request, pk):
        return self._transition_result(
            request, pk, OrderStatus.CONFIRM, Order.get_confirmation_url
        )

    def send_production_view(self, request, pk):
        return self._transition_result(
            request, pk, OrderStatus.PRODUCTION, Order.get_production_url
        )

    def send_shipment_view(self, request, pk):
        return self._transition_result(
            request, pk, OrderStatus.SENT, Order.get_shipment_url
        )

    def send_payment_view(self, request, pk):
        return self._transition_result(request, pk, OrderStatus.PAYMENT)

    def send_paid_view(self, request, pk):
        return self._transition_result(request, pk, OrderStatus.PAID)

    def send_delivered_view(self, request, pk):
        return self._transition_result(request, pk, OrderStatus.DELIVERED)

    def send_canceled_view(self, request, pk):
        return self._transition_result(request, pk, OrderStatus.CANCELED)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "figure", "quantity", "price")
    list_filter = ("order__status",)
    search_fields = ("figure__name", "order__pk")
    readonly_fields = ("figure", "quantity", "price", "order")
