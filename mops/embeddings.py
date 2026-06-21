"""Embedding utilities for document search.

This module provides a simple interface for generating text embeddings.
"""

from mops.services import generate_embedding


def embed_text(text: str) -> list[float]:
    """Generate a vector embedding for the given text.
    
    Args:
        text: The text to embed.
    
    Returns:
        A list of float values representing the embedding vector.
    """
    return generate_embedding(text)
