"""Registry for code-defined agents and tools.

This module provides a central registry for agent factories and tool factories,
allowing them to be registered and retrieved by name/slug.
"""

from typing import Callable
from pydantic_ai import Agent, Tool as PydanticTool

# Registries
_agent_registry: dict[str, Callable] = {}
_tool_factory_registry: dict[str, Callable] = {}


def register_agent(impl_name: str, factory: Callable):
    """Register an agent factory function by implementation name.
    
    Args:
        impl_name: The name to register the agent factory under.
        factory: A callable that returns a pydantic_ai.Agent.
    """
    _agent_registry[impl_name] = factory


def register_tool_factory(tool_slug: str, factory: Callable):
    """Register a tool factory by slug.
    
    The factory must accept **kwargs and return a PydanticAI Tool.
    
    Args:
        tool_slug: The slug to register the tool factory under.
        factory: A callable that accepts **kwargs and returns a PydanticTool.
    """
    _tool_factory_registry[tool_slug] = factory


def get_agent_factory(impl_name: str) -> Callable:
    """Get agent factory by implementation name.
    
    Args:
        impl_name: The registered implementation name.
    
    Returns:
        The agent factory function.
    
    Raises:
        KeyError: If the implementation name is not registered.
    """
    if impl_name not in _agent_registry:
        raise KeyError(f"Agent implementation '{impl_name}' not registered")
    return _agent_registry[impl_name]


def get_tool_factory(tool_slug: str) -> Callable:
    """Get tool factory by slug.
    
    Args:
        tool_slug: The registered tool factory slug.
    
    Returns:
        The tool factory function.
    
    Raises:
        KeyError: If the tool slug is not registered.
    """
    if tool_slug not in _tool_factory_registry:
        raise KeyError(f"Tool factory '{tool_slug}' not registered")
    return _tool_factory_registry[tool_slug]


def list_agents() -> list[str]:
    """List all registered agent implementation names.
    
    Returns:
        A list of registered agent implementation names.
    """
    return list(_agent_registry.keys())


def list_tool_factories() -> list[str]:
    """List all registered tool factory slugs.
    
    Returns:
        A list of registered tool factory slugs.
    """
    return list(_tool_factory_registry.keys())
