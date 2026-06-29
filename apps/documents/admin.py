from django.contrib import admin

from apps.documents.models import Document, DocumentVersion, Tag


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ("version_number", "size_bytes", "checksum", "uploaded_by", "uploaded_at")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "collection", "uploaded_by", "file_type", "status", "created_at")
    list_filter = ("status", "file_type", "created_at", "collection")
    search_fields = ("title", "description")
    raw_id_fields = ("collection", "uploaded_by")
    inlines = [DocumentVersionInline]
    ordering = ("-created_at",)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version_number", "size_bytes", "uploaded_by", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("document__title", "checksum")
    raw_id_fields = ("document", "uploaded_by")
    ordering = ("-uploaded_at",)
