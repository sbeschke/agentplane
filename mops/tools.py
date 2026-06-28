"""Built-in tools for agents.

This module provides built-in tool factories for common operations like
 document search.
"""

from typing import TYPE_CHECKING
from pydantic_ai import Tool as PydanticTool
from mops.decorators import tool

if TYPE_CHECKING:
    from mops.models import Collection


@tool(slug="search_documents")
def search_documents_tool_factory(collections: list["Collection"], **kwargs) -> PydanticTool:
    """Factory for a document search tool.
    
    Creates a PydanticAI Tool that searches across the configured collections.
    
    Args:
        collections: List of Collection objects to search in.
        **kwargs: Additional parameters (unused, for forward compatibility).
    
    Returns:
        A PydanticAI Tool that searches the configured collections.
    """
    def search_documents(query: str) -> str:
        """Search across configured document collections.
        
        Args:
            query: The search query string.
        
        Returns:
            Concatenated content of top matching chunks, or a "not found" message.
        """
        from mops.vector_store import search_similar

        results = []
        for collection in collections:
            chunks = search_similar(collection, query, k=3)
            results.extend([c.content for c in chunks])

        if not results:
            return "No matching documents found."

        return "\n\n".join(results)

    return PydanticTool(search_documents)


@tool(slug="get_weather")
def get_weather_tool_factory(**kwargs) -> PydanticTool:
    """Factory for a weather tool (example stateless tool).
    
    Returns a PydanticAI Tool that doesn't require runtime configuration.
    
    Returns:
        A PydanticAI Tool for getting weather information.
    """
    def get_weather(city: str) -> str:
        """Get weather information for a city.
        
        Args:
            city: The city name.
        
        Returns:
            A weather description string.
        """
        # In a real app, this would call a weather API
        return f"The weather in {city} is sunny and 72°F."

    return PydanticTool(get_weather)
