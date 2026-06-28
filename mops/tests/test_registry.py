"""Tests for the registry module."""

from django.test import TestCase
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import (
    register_agent,
    register_tool_factory,
    get_agent_factory,
    get_tool_factory,
    list_agents,
    list_tool_factories,
)


class TestAgentRegistry(TestCase):
    """Tests for agent registry functions."""

    def test_register_and_get_agent(self):
        """Test registering and retrieving an agent factory."""
        def my_agent(prompt):
            return Agent(instructions=prompt)

        register_agent("my_agent", my_agent)
        self.assertIn("my_agent", list_agents())
        self.assertIs(get_agent_factory("my_agent"), my_agent)

    def test_get_nonexistent_agent(self):
        """Test getting a non-existent agent raises KeyError."""
        with self.assertRaises(KeyError):
            get_agent_factory("nonexistent")

    def test_list_agents_empty(self):
        """Test listing agents when registry is empty."""
        # Clear the registry (for this test only)
        from mops.registry import _agent_registry
        original = _agent_registry.copy()
        _agent_registry.clear()
        try:
            self.assertEqual(list_agents(), [])
        finally:
            _agent_registry.update(original)


class TestToolFactoryRegistry(TestCase):
    """Tests for tool factory registry functions."""

    def test_register_and_get_tool_factory(self):
        """Test registering and retrieving a tool factory."""
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        register_tool_factory("my_tool", my_tool_factory)
        self.assertIn("my_tool", list_tool_factories())
        self.assertIs(get_tool_factory("my_tool"), my_tool_factory)

    def test_get_nonexistent_tool_factory(self):
        """Test getting a non-existent tool factory raises KeyError."""
        with self.assertRaises(KeyError):
            get_tool_factory("nonexistent")

    def test_list_tool_factories_empty(self):
        """Test listing tool factories when registry is empty."""
        from mops.registry import _tool_factory_registry
        original = _tool_factory_registry.copy()
        _tool_factory_registry.clear()
        try:
            self.assertEqual(list_tool_factories(), [])
        finally:
            _tool_factory_registry.update(original)
