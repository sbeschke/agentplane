"""Tests for the decorators module."""

from django.test import TestCase
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import list_agents, list_tool_factories, get_agent_factory, get_tool_factory
from mops.decorators import agent, tool


class TestAgentDecorator(TestCase):
    """Tests for the @agent decorator."""

    def test_agent_decorator_registers_function(self):
        """Test that @agent decorator registers the function."""
        @agent
        def my_agent(prompt) -> Agent:
            return Agent(instructions="test")

        self.assertIn("my_agent", list_agents())
        self.assertIs(get_agent_factory("my_agent"), my_agent)

    def test_agent_decorator_returns_function(self):
        """Test that @agent decorator returns the original function."""
        @agent
        def my_agent(prompt) -> Agent:
            return Agent(instructions="test")

        self.assertTrue(callable(my_agent))

    def test_agent_decorator_preserves_function_name(self):
        """Test that the function name is preserved."""
        @agent
        def custom_agent_name(prompt) -> Agent:
            return Agent(instructions="test")

        self.assertIn("custom_agent_name", list_agents())


class TestToolDecorator(TestCase):
    """Tests for the @tool decorator."""

    def test_tool_decorator_registers_factory(self):
        """Test that @tool decorator registers the factory."""
        @tool
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        self.assertIn("my_tool_factory", list_tool_factories())
        self.assertIs(get_tool_factory("my_tool_factory"), my_tool_factory)

    def test_tool_decorator_returns_original_function(self):
        """Test that @tool decorator returns the original factory function."""
        @tool
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        # Should return the original factory function
        self.assertTrue(callable(my_tool_factory))

    def test_tool_decorator_with_custom_slug(self):
        """Test @tool decorator with custom slug."""
        @tool(slug="custom_slug")
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        self.assertIn("custom_slug", list_tool_factories())
        self.assertIs(get_tool_factory("custom_slug"), my_tool_factory)

    def test_tool_decorator_without_slug_uses_function_name(self):
        """Test that @tool without slug uses the function name."""
        @tool
        def weather_tool_factory(**kwargs):
            def weather(city: str) -> str:
                return f"Sunny in {city}"
            return PydanticTool(weather)

        self.assertIn("weather_tool_factory", list_tool_factories())
