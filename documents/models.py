from django.db import models
from pgvector.django import VectorField


class Collection(models.Model):
    """A set of documents to be indexed and searched (RAG)."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


def get_document_upload_path(instance, filename):
    """Generate upload path for document files."""
    # Use pk which works for both saved and unsaved instances
    collection_id = instance.collection.pk if instance.collection else "unsorted"
    return f"documents/collection_{collection_id}/{filename}"


class Document(models.Model):
    """A document uploaded to a collection for indexing."""

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.FileField(upload_to=get_document_upload_path)
    name = models.CharField(max_length=255, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(
        null=True, blank=True, help_text="Size in bytes"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["collection", "created_at"]),
            models.Index(fields=["id"]),  # For efficient ordering by ID
        ]

    def __str__(self):
        return self.name or self.original_filename

    def save(self, *args, **kwargs):
        # For new uploads (UploadedFile), capture metadata before Django converts to File
        if hasattr(self, "_file") and self._file and not self.mime_type:
            # _file is the UploadedFile before it's saved
            if hasattr(self._file, "content_type") and self._file.content_type:
                self.mime_type = self._file.content_type

        if self.file:
            if not self.original_filename:
                self.original_filename = self.file.name
            if not self.name:
                self.name = self.original_filename
            if not self.file_size:
                self.file_size = self.file.size
            if not self.mime_type:
                self.mime_type = "application/octet-stream"
        super().save(*args, **kwargs)


class DocumentChunk(models.Model):
    """A chunk of a document with its vector embedding for similarity search."""

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="chunks"
    )
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()
    embedding = VectorField(
        dimensions=384
    )  # all-MiniLM-L6-v2 produces 384-dim embeddings
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("document", "chunk_index")
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document}"
