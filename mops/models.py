"""Models for django-mops-agents.

Merged from agents/models.py and documents/models.py.
"""

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

from django.db import models


# =============================================================================
# pgvector Support - Optional Dependency
# =============================================================================


def _pgvector_available() -> bool:
    """Check if pgvector is installed and available."""
    import importlib.util

    return importlib.util.find_spec("pgvector") is not None


def _using_postgresql() -> bool:
    """Check if the database backend is PostgreSQL."""
    from django.db import connection

    return connection.vendor == "postgresql"


# Define VectorField based on pgvector availability and database backend
# Only use ArrayField if both pgvector is installed AND we're using PostgreSQL
if _pgvector_available() and _using_postgresql():
    from django.contrib.postgres.fields import ArrayField

    # Create a proper VectorField class that wraps ArrayField
    class VectorField(ArrayField):
        """A vector field for storing embeddings when pgvector is available."""

        def __init__(self, *args, **kwargs):
            # Set default size for embeddings (384 for all-MiniLM-L6-v2)
            kwargs.setdefault("size", 384)
            super().__init__(models.FloatField(), *args, **kwargs)
else:
    # Fallback to JSONField for storing vector embeddings
    # This is used when pgvector is not installed OR when not using PostgreSQL
    VectorField = models.JSONField


# =============================================================================
# Agent Models (from agents/models.py)
# =============================================================================


class Agent(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    instructions = models.TextField(blank=True, null=True)
    llm_provider = models.ForeignKey(
        "LLMProvider",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="LLM provider for this agent",
    )
    model_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Model name to use (must be available in the selected provider)",
    )

    # Search configuration
    search_enabled = models.BooleanField(
        default=False,
        help_text="Enable document search tool for this agent",
    )
    allowed_collections = models.ManyToManyField(
        "Collection",
        blank=True,
        help_text="Collections this agent can search",
    )

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.llm_provider and self.model_name:
            if self.model_name not in self.llm_provider.available_models:
                raise ValidationError(
                    f"Model '{self.model_name}' is not available in provider "
                    f"'{self.llm_provider.name}'. "
                    f"Available models: {', '.join(self.llm_provider.available_models)}"
                )


class Conversation(models.Model):
    """Model to store conversations with agents.

    Each conversation is linked to a specific agent and contains a list of events
    (messages, responses, etc.).

    Events are stored in a JSONField as a list of dictionaries, where each dictionary
    represents an event. The format follows the PydanticAI format.
    """

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="conversations"
    )
    history = models.JSONField(
        default=list
    )  # Store the conversation history as a list of PydanticAI messages in JSON format
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation with {self.agent.name} at {self.created_at}"

    def get_history(self) -> list[ModelMessage]:
        """Get the conversation history as a list of ModelMessage objects."""
        return ModelMessagesTypeAdapter.validate_python(self.history)

    def set_history(self, messages: list[ModelMessage]):
        """Set the conversation history."""
        self.history = to_jsonable_python(messages)
        self.save()


class LLMProvider(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(
        help_text="Base URL for an OpenAI-compatible HTTP API (include /v1), "
        "e.g. http://127.0.0.1:8765/v1"
    )
    available_models = models.JSONField(
        default=list, help_text="List of available model names"
    )
    last_discovered = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


# =============================================================================
# Document Models (from documents/models.py)
# =============================================================================


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
    # Use VectorField if pgvector is available, otherwise fall back to JSONField
    embedding = VectorField(default=list, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("document", "chunk_index")
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document}"
