"""Built-in agent implementations.

This module provides built-in agent implementations for code-defined agents.
"""

from pydantic_ai import Agent
from mops.decorators import agent
from mops.models import Prompt, LLMProvider, Collection


@agent
def legacy_agent(
    prompt: Prompt,
    llm: LLMProvider | None = None,
    collections: list[Collection] | None = None,
) -> Agent:
    """Legacy agent wrapper that mimics the old Agent model behavior.
    
    Used during migration from the old Agent model to the new code-defined agents.
    
    Args:
        prompt: The prompt for the agent.
        llm: The LLM provider (optional).
        collections: List of collections for RAG (optional).
    
    Returns:
        A pydantic_ai.Agent configured with the provided dependencies.
    """
    # Build model config
    model_config = {}
    if llm and llm.default_model:
        model_config["model"] = llm.default_model

    # Build tools
    tools = []
    if collections:
        from mops.tools import search_documents_tool_factory
        # Create a search tool configured for these collections
        search_tool = search_documents_tool_factory(collections=collections)
        tools.append(search_tool)

    return Agent(
        instructions=prompt.text,
        tools=tools,
        **model_config
    )
