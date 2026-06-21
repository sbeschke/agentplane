"""
Example agents for django-mops.
Demonstrates code-defined agent patterns.
"""

from pydantic_ai import Agent, Tool as PydanticTool
from mops.decorators import agent, tool
from mops.models import Prompt, LLMProvider, Collection


# =============================================================================
# Tools
# =============================================================================

@tool(slug="get_weather")
def get_weather_tool_factory(**kwargs) -> PydanticTool:
    """Factory for a weather tool (stateless)."""
    def get_weather(city: str) -> str:
        """Get weather information for a city."""
        # In a real app, this would call a weather API
        return f"The weather in {city} is sunny and 72°F."

    return PydanticTool(get_weather)


@tool(slug="calculate")
def calculate_tool_factory(**kwargs) -> PydanticTool:
    """Factory for a calculation tool (stateless)."""
    def calculate(a: int, b: int, operation: str = "add") -> int:
        """Perform a calculation."""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        else:
            return a // b

    return PydanticTool(calculate)


@tool(slug="search_documents")
def search_documents_tool_factory(collections: list[Collection], **kwargs) -> PydanticTool:
    """
    Factory for a document search tool (parameterized).
    Requires 'collections' parameter in ToolConfig.
    """
    def search_documents(query: str) -> str:
        """Search across configured document collections."""
        from mops.vector_store import search_similar

        results = []
        for collection in collections:
            chunks = search_similar(collection, query, k=3)
            results.extend([c.content for c in chunks])

        if not results:
            return "No matching documents found."

        return "\n\n".join(results)

    return PydanticTool(search_documents)


# =============================================================================
# Agents
# =============================================================================

@agent
def simple_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
    """
    A simple agent that just uses a prompt and LLM provider.
    """
    model_config = {}
    if llm.default_model:
        model_config["model"] = llm.default_model

    return Agent(
        instructions=prompt.text,
        **model_config
    )


@agent
def weather_agent(
    prompt: Prompt,
    llm: LLMProvider,
    weather_tool: PydanticTool,  # Injected from ToolConfig
) -> Agent:
    """
    An agent that can answer weather questions using the get_weather tool.
    """
    model_config = {}
    if llm.default_model:
        model_config["model"] = llm.default_model

    return Agent(
        instructions=prompt.text,
        tools=[weather_tool],
        **model_config
    )


@agent
def rag_agent(
    prompt: Prompt,
    llm: LLMProvider,
    search_tool: PydanticTool,  # Injected from ToolConfig (search_documents with collections)
) -> Agent:
    """
    A RAG agent that can search documents in configured collections.
    """
    model_config = {}
    if llm.default_model:
        model_config["model"] = llm.default_model

    return Agent(
        instructions=prompt.text,
        tools=[search_tool],
        **model_config
    )


@agent
def multi_tool_agent(
    prompt: Prompt,
    llm: LLMProvider,
    weather_tool: PydanticTool,
    calc_tool: PydanticTool,
) -> Agent:
    """
    An agent with multiple specific tools injected.
    """
    model_config = {}
    if llm.default_model:
        model_config["model"] = llm.default_model

    return Agent(
        instructions=prompt.text,
        tools=[weather_tool, calc_tool],
        **model_config
    )


@agent
def kitchen_sink_agent(
    prompt: Prompt,
    llm: LLMProvider,
    collections: list[Collection],
    tools: list[PydanticTool],
) -> Agent:
    """
    An agent with all possible dependencies.
    Demonstrates how to pass multiple collections and tools.
    """
    model_config = {}
    if llm.default_model:
        model_config["model"] = llm.default_model

    return Agent(
        instructions=prompt.text,
        tools=tools,
        **model_config
    )
