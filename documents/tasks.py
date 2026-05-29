"""Background tasks for document processing."""

import logging

import django_tasks

logger = logging.getLogger(__name__)


@django_tasks.task
def process_document_task(document_id: int) -> None:
    """Background task to index a document after upload.

    Args:
        document_id: ID of the Document to process
    """
    try:
        from documents.models import Document
        from documents.services import index_document

        document = Document.objects.get(id=document_id)
        index_document(document)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for indexing")
    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {e}")
