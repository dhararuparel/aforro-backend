from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ["product"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "store", "status", "created_at"]
    list_filter = ["status", "store"]
    search_fields = ["store__name"]
    list_select_related = ["store"]
    inlines = [OrderItemInline]
    ordering = ["-created_at"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity_requested"]
    list_select_related = ["order", "product"]
    raw_id_fields = ["order", "product"]
