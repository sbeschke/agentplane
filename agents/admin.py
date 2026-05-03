from django.contrib import admin
from django.contrib import messages
from .models import Agent, LLMProvider
from .services import discover_models


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "llm_provider", "model_name", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", "llm_provider")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Basic Information", {"fields": ("name", "slug", "description")}),
        ("Configuration", {"fields": ("instructions", "llm_provider", "model_name")}),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "model_count", "last_discovered")
    readonly_fields = ("available_models", "last_discovered")
    fieldsets = (
        ("Provider Details", {"fields": ("name", "url")}),
        ("Models", {"fields": ("available_models", "last_discovered")}),
    )
    actions = ["refresh_models"]

    def model_count(self, obj):
        return len(obj.available_models)

    model_count.short_description = "Available Models"

    def refresh_models(self, request, queryset):
        for provider in queryset:
            models = discover_models(provider)
            if models:
                self.message_user(
                    request,
                    f"Successfully discovered {len(models)} models for {provider.name}.",
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    f"Failed to discover models for {provider.name}. Check the URL and connection.",
                    messages.ERROR,
                )

    refresh_models.short_description = "Refresh available models"
