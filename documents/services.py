"""Document processing services for RAG: PDF extraction, chunking, and embeddings."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from sentence_transformers import SentenceTransformer

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

if TYPE_CHECKING:
    from documents.models import Collection, Document, DocumentChunk

logger = logging.getLogger(__name__)


# Lazy-loaded embedding model singleton
_EMBEDDING_MODEL: Optional[SentenceTransformer] = None


def get_embedding_model() -> "SentenceTransformer":
    """Get or initialize the embedding model (lazy-loaded singleton).

    Uses all-MiniLM-L6-v2 which produces 384-dimensional embeddings.
    """
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
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
    from django.db import connection
    from pgvector.django import L2Distance
    from documents.models import DocumentChunk

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
    # L2Distance only works with PostgreSQL; for other backends, use brute-force
    if connection.vendor == "postgresql":
        chunks = chunks.annotate(
            distance=L2Distance("embedding", query_embedding)
        ).order_by("distance")[:limit]
    else:
        # Fallback for non-PostgreSQL backends (e.g., SQLite during testing)
        # This is slower but works without pgvector
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
    from documents.models import DocumentChunk

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
