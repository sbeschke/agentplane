"""Services for django-mops-agents.

Merged from agents/services.py and documents/services.py.
"""

from __future__ import annotations

import django_tasks
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import connection
from django.utils import timezone

import openai
from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from mops.conf import (
    get_local_llm_base_url,
    get_local_llm_model,
    get_openai_compat_api_key,
)

if TYPE_CHECKING:
    from mops.models import (
        Agent as AgentModel,
        Collection,
        Conversation,
        Document,
        DocumentChunk,
        LLMProvider,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Services (from agents/services.py)
# =============================================================================

def _openai_provider(base_url: str, api_key: str = None) -> OpenAIProvider:
    return OpenAIProvider(
        base_url=base_url,
        api_key=api_key or get_openai_compat_api_key(),
    )


def discover_models(provider: "LLMProvider") -> list[str]:
    """Discover available models from the LLM provider."""
    try:
        # Use a valid-looking key format for local providers
        client = openai.OpenAI(
            base_url=provider.url,
            api_key=get_openai_compat_api_key(),
        )
        models = client.models.list()
        model_names = [model.id for model in models.data]
        provider.available_models = model_names
        provider.last_discovered = timezone.now()
        provider.save(update_fields=["available_models", "last_discovered"])
        return model_names
    except Exception as e:
        print(f"Error discovering models for {provider.name}: {e}")
        return []


@django_tasks.task
def run_agent_chat_task(conversation_id: int, message: str):
    """Background task to handle LLM chat and update conversation history."""
    from mops.models import Conversation

    conversation = Conversation.objects.get(id=conversation_id)
    chat(conversation, message)


def _create_search_tool(agent: "AgentModel") -> Tool | None:
    """Create a document search tool for the agent if search is enabled.

    Args:
        agent: Agent instance

    Returns:
        pydantic_ai Tool instance or None if search is not enabled
    """
    if not agent.search_enabled:
        return None

    # Get the collections this agent can search
    collections = list(agent.allowed_collections.all())
    if not collections:
        return None

    def search_documents(query: str) -> str:
        """Search documents and return formatted results."""
        chunks = search_chunks(query, collections=collections, limit=3)

        if not chunks:
            return "No relevant documents found."

        results = []
        for i, chunk in enumerate(chunks, 1):
            results.append(
                f"Result {i}:\n"
                f"Document: {chunk.document.name}\n"
                f"Content: {chunk.content[:200]}..."
            )

        return "\n\n".join(results)

    return Tool(
        name="search_documents",
        description=f"Search documents in collections: {', '.join(c.name for c in collections)}",
        function=search_documents,
    )


def _build_pydantic_agent(agent: "AgentModel") -> Agent:
    """Build a pydantic_ai Agent with optional search tools.

    Args:
        agent: Agent instance

    Returns:
        pydantic_ai Agent instance
    """
    # Build the base model
    if agent.llm_provider and agent.model_name:
        model = OpenAIChatModel(
            agent.model_name, provider=_openai_provider(agent.llm_provider.url)
        )
    else:
        model = OpenAIChatModel(
            get_local_llm_model(),
            provider=_openai_provider(get_local_llm_base_url()),
        )

    # Build tools list
    tools = []
    search_tool = _create_search_tool(agent)
    if search_tool:
        tools.append(search_tool)

    # Create the agent
    if tools:
        return Agent(
            model,
            instructions=agent.instructions,
            tools=tools,
        )
    else:
        return Agent(
            model,
            instructions=agent.instructions,
        )


def chat(conversation: "Conversation", message: str) -> None:
    """Schedules the background task for chatting."""
    try:
        history = conversation.get_history()
        agent = conversation.agent

        pydantic_agent = _build_pydantic_agent(agent)

        result = pydantic_agent.run_sync(message, message_history=history)
        conversation.set_history(result.all_messages())
    except Exception as e:
        # In a real app, we might want to log this or store the error in the conversation history
        # For now, let's just print it.
        print(f"Error in background task for conversation {conversation.id}: {e}")
        pass


# =============================================================================
# Document Services (from documents/services.py)
# =============================================================================

# Lazy-loaded embedding model singleton
_EMBEDDING_MODEL: Optional["SentenceTransformer"] = None


def get_embedding_model() -> "SentenceTransformer":
    """Get or initialize the embedding model (lazy-loaded singleton).

    Uses all-MiniLM-L6-v2 which produces 384-dimensional embeddings.
    """
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for embedding generation. "
                "Install it with: pip install sentence-transformers"
            )

        model_cache_dir = Path(settings.BASE_DIR) / ".cache" / "sentence-transformers"
        model_cache_dir.mkdir(parents=True, exist_ok=True)

        _EMBEDDING_MODEL = SentenceTransformer(
            "all-MiniLM-L6-v2",
            cache_folder=str(model_cache_dir),
        )
    return _EMBEDDING_MODEL


def extract_text_from_pdf(file_path: str | Path | UploadedFile) -> str:
    """Extract text content from a PDF file.

    Args:
        file_path: Path to PDF file or UploadedFile object

    Returns:
        Extracted text as a single string

    Raises:
        ValueError: If the file cannot be read or is not a valid PDF
    """

    if isinstance(file_path, UploadedFile):
        # Save to temp file for reading
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in file_path.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            text = _extract_text_from_path(tmp_path)
        finally:
            os.unlink(tmp_path)
        return text

    return _extract_text_from_path(file_path)


def _extract_text_from_path(file_path: str | Path) -> str:
    """Internal function to extract text from a file path."""
    from pypdf import PdfReader

    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)


def chunk_text(
    text: str | None,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        overlap: Overlap between chunks in characters

    Returns:
        List of text chunks
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)

        # Move start forward by (chunk_size - overlap) for the next chunk
        if end == text_length:
            break
        start = end - overlap

        # Ensure we make progress even if overlap >= chunk_size
        if start <= 0:
            start = end

    return chunks


def generate_embedding(text: str) -> list[float]:
    """Generate a vector embedding for the given text.

    Args:
        text: Text to embed

    Returns:
        List of float values representing the embedding vector
    """
    model = get_embedding_model()
    return model.encode(text).tolist()


def search_chunks(
    query: str,
    collections: list["Collection"] | None = None,
    limit: int = 5,
) -> list["DocumentChunk"]:
    """Search for document chunks similar to the query.

    Args:
        query: Search query text
        collections: Optional list of Collection instances to search in
        limit: Maximum number of results to return

    Returns:
        List of DocumentChunk instances sorted by similarity (most similar first)
    """
    from mops.models import DocumentChunk

    # Generate embedding for the query
    query_embedding = generate_embedding(query)

    # Build the query
    if collections is not None and len(collections) > 0:
        # Filter by collections
        chunks = DocumentChunk.objects.filter(document__collection__in=collections)
    elif collections is not None:
        # Empty list - return no results
        return []
    else:
        chunks = DocumentChunk.objects.all()

    # Add distance annotation and order by similarity
    # For now, use brute-force since pgvector is optional
    # When pgvector is available, this can be optimized
    all_chunks = list(chunks[:100])  # Limit for performance

    def l2_distance(embedding1, embedding2):
        """Calculate L2 distance between two embeddings."""
        return sum((a - b) ** 2 for a, b in zip(embedding1, embedding2)) ** 0.5

    # Sort by distance in Python
    all_chunks.sort(key=lambda c: l2_distance(c.embedding, query_embedding))
    chunks = all_chunks[:limit]

    return chunks


def index_document(document: "Document") -> None:
    """Process a document: extract text, chunk it, generate embeddings, and store chunks.

    This is the main entry point for document indexing. Called by the background task.

    Args:
        document: Document instance to index
    """
    from django.core.files.storage import default_storage
    from mops.models import DocumentChunk

    if not document.file:
        return

    # Extract text from PDF
    try:
        file_path = default_storage.path(document.file.name)
        text = extract_text_from_pdf(file_path)
    except Exception as e:
        # Log error
        logger.exception(f"Error extracting text from document {document.id}: {e}")
        return

    if not text:
        logger.warning(f"No text extracted from document {document.id}")
        return

    # Chunk the text
    chunks = chunk_text(text, chunk_size=1000, overlap=200)

    if not chunks:
        logger.warning(f"No chunks created for document {document.id}")
        return

    # Generate embeddings and create DocumentChunk instances
    for i, chunk in enumerate(chunks):
        try:
            embedding = generate_embedding(chunk)

            DocumentChunk.objects.create(
                document=document,
                content=chunk,
                chunk_index=i,
                embedding=embedding,
                metadata={
                    "char_count": len(chunk),
                    "word_count": len(chunk.split()),
                },
            )
        except Exception as e:
            logger.exception(
                f"Error processing chunk {i} of document {document.id}: {e}"
            )
            continue

    logger.info(
        f"Successfully indexed document {document.id} with {len(chunks)} chunks"
    )


# =============================================================================
# Background Tasks (from documents/tasks.py)
# =============================================================================

@django_tasks.task
def process_document_task(document_id: int) -> None:
    """Background task to index a document after upload.

    Args:
        document_id: ID of the Document to process
    """
    try:
        from mops.models import Document

        document = Document.objects.get(id=document_id)
        index_document(document)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for indexing")
    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {e}")
