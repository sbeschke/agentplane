from django.contrib import admin

from documents.models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at", "updated_at")
