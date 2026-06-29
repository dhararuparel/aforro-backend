from django.contrib import admin

from apps.collections.models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at", "updated_at")
    list_filter = ("created_by", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
