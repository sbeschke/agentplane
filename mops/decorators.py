"""Decorators for code-defined agents and tools.

This module provides decorators for registering agent factories and tool factories.
"""

from typing import Callable, Union

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


def tool(
    arg: Union[str, Callable, None] = None, *, slug: str | None = None
) -> Union[Callable, Callable]:
    """Decorator to register a tool factory function.

    The decorated function must accept **kwargs and return a PydanticAI Tool.
    The function is registered by the provided slug or its __name__.

    Can be used in two ways:
    1. With parentheses: @tool(slug="my_tool")
    2. Without parentheses: @tool

    Args:
        arg: Either a function (when used without parentheses) or a slug string.
        slug: Optional slug to register the tool factory under (keyword-only).

    Returns:
        A decorator function or the original function if called without parentheses.

    Example:
        @tool(slug="search_documents")
        def search_documents_tool_factory(collections: list[Collection], **kwargs) -> PydanticTool:
            def search(query: str) -> str:
                # ... search logic
                return "results"
            return PydanticTool(search)

        @tool
        def my_tool_factory(**kwargs) -> PydanticTool:
            return PydanticTool(...)
    """
    # Case 1: @tool (without parentheses)
    if callable(arg):
        func = arg
        registry_slug = slug or func.__name__
        register_tool_factory(registry_slug, func)
        return func

    # Case 2: @tool(slug="...") or @tool()
    def decorator(func: Callable):
        registry_slug = slug or arg or func.__name__
        register_tool_factory(registry_slug, func)
        return func  # Returns the original factory function

    return decorator
