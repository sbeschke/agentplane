"""Admin configuration for django-mops-agents.

Merged from agents/admin.py and documents/admin.py.
"""

from django.contrib import admin

from mops.models import (
    Agent,
    Collection,
    Conversation,
    Document,
    DocumentChunk,
    LLMProvider,
)


# =============================================================================
# Agent Admin (from agents/admin.py)
# =============================================================================


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug", "description", "instructions")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "slug", "description"),
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "instructions",
                    "llm_provider",
                    "model_name",
                    "search_enabled",
                    "allowed_collections",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    filter_horizontal = ("allowed_collections",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "agent", "created_at", "updated_at")
    search_fields = ("agent__name", "id")
    readonly_fields = ("created_at", "updated_at", "history")
    list_filter = ("agent",)


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "last_discovered")
    search_fields = ("name", "url")
    readonly_fields = ("last_discovered",)


# =============================================================================
# Document Admin (from documents/admin.py)
# =============================================================================


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    readonly_fields = ("created_at", "updated_at", "file_size")
    fields = ("file", "name", "original_filename", "file_size", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("collection")


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ("chunk_index", "created_at")
    fields = ("chunk_index", "content", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("document")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug", "document_count", "created_at", "updated_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at", "updated_at", "document_count")
    inlines = [DocumentInline]

    def document_count(self, obj):
        return obj.documents.count()

    document_count.short_description = "Documents"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "collection",
        "original_filename",
        "file_size",
        "chunk_count",
        "created_at",
    )
    list_filter = ("collection",)
    search_fields = ("name", "original_filename", "collection__name")
    readonly_fields = (
        "created_at",
        "updated_at",
        "original_filename",
        "file_size",
        "chunk_count",
    )
    fieldsets = (
        ("Basic Information", {"fields": ("collection", "file", "name", "metadata")}),
        ("File Details", {"fields": ("original_filename", "mime_type", "file_size")}),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at", "chunk_count"),
                "classes": ("collapse",),
            },
        ),
    )
    inlines = [DocumentChunkInline]

    def chunk_count(self, obj):
        return obj.chunks.count()

    chunk_count.short_description = "Chunks"

    def save_model(self, request, obj, form, change):
        """Capture file metadata from UploadedFile before save."""
        if obj.file and hasattr(obj.file, "content_type"):
            # This is a newly uploaded file (UploadedFile)
            if not obj.mime_type:
                obj.mime_type = obj.file.content_type or ""
            if not obj.original_filename:
                obj.original_filename = obj.file.name or ""
            if not obj.file_size:
                obj.file_size = obj.file.size
            if not obj.name:
                obj.name = obj.original_filename or obj.file.name or ""
        super().save_model(request, obj, form, change)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "chunk_index", "created_at")
    list_filter = ("document__collection",)
    search_fields = ("document__name", "content")
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("document", "chunk_index", "content"),
            },
        ),
        (
            "Embedding",
            {
                "fields": ("embedding", "metadata"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )
