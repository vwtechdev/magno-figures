from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path

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
    )
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {"fields": ("user", "address", "status", "tracking_code")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )

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

    def _transition_result(self, request, pk, status, url_getter):
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
        return JsonResponse({"url": url_getter(order)})

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


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "figure", "quantity", "price")
    list_filter = ("order__status",)
    search_fields = ("figure__name", "order__pk")
    readonly_fields = ("figure", "quantity", "price", "order")
