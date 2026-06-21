"""Decorators for code-defined agents and tools.

This module provides decorators for registering agent factories and tool factories.
"""

from functools import wraps
from typing import Callable
from pydantic_ai import Tool as PydanticTool
from mops.registry import register_agent, register_tool_factory


def agent(func: Callable) -> Callable:
    """Decorator to register an agent factory function.
    
    The decorated function must return a pydantic_ai.Agent.
    The function is registered by its __name__ attribute.
    
    Args:
        func: An agent factory function that returns a pydantic_ai.Agent.
    
    Returns:
        The original function (unchanged).
    
    Example:
        @agent
        def my_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
            return Agent(instructions=prompt.text, model=llm.default_model)
    """
    register_agent(func.__name__, func)
    return func


def tool(*, slug: str | None = None):
    """Decorator to register a tool factory function.
    
    The decorated function must accept **kwargs and return a PydanticAI Tool.
    The function is registered by the provided slug or its __name__.
    
    Args:
        slug: Optional slug to register the tool factory under.
              If not provided, the function's __name__ is used.
    
    Returns:
        A decorator function that registers the tool factory.
    
    Example:
        @tool(slug="search_documents")
        def search_documents_tool_factory(collections: list[Collection], **kwargs) -> PydanticTool:
            def search(query: str) -> str:
                # ... search logic
                return "results"
            return PydanticTool(search)
    """
    def decorator(func: Callable):
        registry_slug = slug or func.__name__
        register_tool_factory(registry_slug, func)
        return func  # Returns the original factory function
    return decorator
