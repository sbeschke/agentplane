"""Vector store utilities for document search.

This module provides utilities for vector similarity search using pgvector.
"""

from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from mops.models import Collection, DocumentChunk


def search_similar(
    collection: "Collection",
    query: str,
    k: int = 3,
    embedding_func: Optional[Callable[[str], list[float]]] = None,
) -> list["DocumentChunk"]:
    """Search for similar document chunks in a collection.

    Args:
        collection: The Collection instance to search in.
        query: The search query text.
        k: Number of results to return.
        embedding_func: Optional function to generate embeddings.
                       If not provided, uses the default embedding function.

    Returns:
        A list of DocumentChunk objects, ordered by similarity.
    """
    from mops.models import DocumentChunk

    if embedding_func is None:
        from mops.embeddings import embed_text

        embedding_func = embed_text

    return DocumentChunk.objects.filter(document__collection=collection).order_by(
        "embedding <-> %s"
    )[:k]
