"""Signals for django-mops-agents.

Merged from agents/signals.py and documents/signals.py.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from mops.models import Document, AgentConfig
from mops.services import process_document_task
from mops.resolver import validate_agent_config, DependencyNotFoundError, InvalidTypeError


@receiver(post_save, sender=Document)
def on_document_saved(sender, instance: Document, created: bool, **kwargs):
    """Trigger document processing when a new document with a file is created.

    Only triggers on creation (not updates) and only if the document has a file.
    Uses instance.pk to check if this is a new save vs an update of an existing record.
    """
    # Only process on creation (not updates) and when file is present
    # instance.pk is None for new objects before save, so created=True means new record
    if created and instance.file:
        # Schedule background task for indexing
        process_document_task.enqueue(instance.id)


@receiver(pre_save, sender=AgentConfig)
def validate_agent_config_on_save(sender, instance: AgentConfig, **kwargs):
    """Validate AgentConfig before saving.
    
    Checks that the implementation is registered and that the parameters
    match the agent factory's signature.
    
    Args:
        sender: The AgentConfig model class.
        instance: The AgentConfig instance being saved.
        **kwargs: Additional signal arguments.
    
    Raises:
        ValueError: If the configuration is invalid.
    """
    errors = validate_agent_config(instance)
    if errors:
        raise ValueError("; ".join(errors))
