from django.contrib import admin

from apps.orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("figure", "quantity", "price")
    readonly_fields = ("figure", "quantity", "price")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__name", "pk")
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
        (None, {"fields": ("user", "address", "status")}),
        ("Metadados", {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "figure", "quantity", "price")
    list_filter = ("order__status",)
    search_fields = ("figure__name", "order__pk")
    readonly_fields = ("figure", "quantity", "price", "order")
