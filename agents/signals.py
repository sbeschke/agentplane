from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from . import models
from .services import discover_models


@receiver(post_save, sender=models.LLMProvider)
def discover_provider_models(sender, instance, created, **kwargs):
    """Automatically discover models when a provider is created or updated."""
    if created or instance.url != instance._original_url:
        discover_models(instance)


# Store original URL for comparison
@receiver(pre_save, sender=models.LLMProvider)
def store_original_url(sender, instance, **kwargs):
    if not hasattr(instance, "_original_url"):
        instance._original_url = instance.url
