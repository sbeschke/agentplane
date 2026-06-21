"""Tests for the decorators module."""

import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import list_agents, list_tool_factories, get_agent_factory, get_tool_factory
from mops.decorators import agent, tool


class TestAgentDecorator:
    """Tests for the @agent decorator."""

    def test_agent_decorator_registers_function(self):
        """Test that @agent decorator registers the function."""
        @agent
        def my_agent(prompt) -> Agent:
            return Agent(instructions="test")

        assert "my_agent" in list_agents()
        assert get_agent_factory("my_agent") is my_agent

    def test_agent_decorator_returns_function(self):
        """Test that @agent decorator returns the original function."""
        @agent
        def my_agent(prompt) -> Agent:
            return Agent(instructions="test")

        assert callable(my_agent)

    def test_agent_decorator_preserves_function_name(self):
        """Test that the function name is preserved."""
        @agent
        def custom_agent_name(prompt) -> Agent:
            return Agent(instructions="test")

        assert "custom_agent_name" in list_agents()


class TestToolDecorator:
    """Tests for the @tool decorator."""

    def test_tool_decorator_registers_factory(self):
        """Test that @tool decorator registers the factory."""
        @tool
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        assert "my_tool_factory" in list_tool_factories()
        assert get_tool_factory("my_tool_factory") is my_tool_factory

    def test_tool_decorator_returns_original_function(self):
        """Test that @tool decorator returns the original factory function."""
        @tool
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        # Should return the original factory function
        assert callable(my_tool_factory)

    def test_tool_decorator_with_custom_slug(self):
        """Test @tool decorator with custom slug."""
        @tool(slug="custom_slug")
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        assert "custom_slug" in list_tool_factories()
        assert get_tool_factory("custom_slug") is my_tool_factory

    def test_tool_decorator_without_slug_uses_function_name(self):
        """Test that @tool without slug uses the function name."""
        @tool
        def weather_tool_factory(**kwargs):
            def weather(city: str) -> str:
                return f"Sunny in {city}"
            return PydanticTool(weather)

        assert "weather_tool_factory" in list_tool_factories()
