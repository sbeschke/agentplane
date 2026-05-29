"""Signals for document processing."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from documents.models import Document
from documents.tasks import process_document_task


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
