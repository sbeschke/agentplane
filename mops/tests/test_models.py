"""Tests for the new code-defined agent models."""

from django.test import TestCase
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.registry import register_agent
from pydantic_ai import Agent


class TestPrompt(TestCase):
    """Tests for the Prompt model."""

    def test_create_prompt(self):
        """Test creating a Prompt instance."""
        prompt = Prompt.objects.create(
            slug="test-prompt",
            name="Test Prompt",
            text="You are a helpful assistant.",
            description="A test prompt"
        )
        self.assertEqual(prompt.slug, "test-prompt")
        self.assertEqual(prompt.name, "Test Prompt")
        self.assertEqual(prompt.text, "You are a helpful assistant.")
        self.assertEqual(prompt.description, "A test prompt")

    def test_prompt_str(self):
        """Test Prompt string representation."""
        prompt = Prompt.objects.create(
            slug="test-prompt",
            name="Test Prompt",
            text="Hello"
        )
        self.assertEqual(str(prompt), "Test Prompt")


class TestLLMProvider(TestCase):
    """Tests for the LLMProvider model."""

    def test_create_provider_with_slug_and_default_model(self):
        """Test creating an LLMProvider with slug and default_model."""
        provider = LLMProvider.objects.create(
            slug="openai",
            name="OpenAI",
            url="https://api.openai.com/v1",
            available_models=["gpt-4", "gpt-3.5-turbo"],
            default_model="gpt-4"
        )
        self.assertEqual(provider.slug, "openai")
        self.assertEqual(provider.name, "OpenAI")
        self.assertEqual(provider.default_model, "gpt-4")
        self.assertEqual(provider.available_models, ["gpt-4", "gpt-3.5-turbo"])

    def test_provider_str(self):
        """Test LLMProvider string representation."""
        provider = LLMProvider.objects.create(
            slug="local",
            name="Local LLM",
            url="http://localhost:8000/v1"
        )
        self.assertEqual(str(provider), "Local LLM")


class TestToolConfig(TestCase):
    """Tests for the ToolConfig model."""

    def test_create_tool_config(self):
        """Test creating a ToolConfig instance."""
        config = ToolConfig.objects.create(
            slug="search-config",
            name="Search Config",
            tool_slug="search_documents",
            parameters={"collections": ["docs", "manuals"]}
        )
        self.assertEqual(config.slug, "search-config")
        self.assertEqual(config.name, "Search Config")
        self.assertEqual(config.tool_slug, "search_documents")
        self.assertEqual(config.parameters, {"collections": ["docs", "manuals"]})

    def test_tool_config_str(self):
        """Test ToolConfig string representation."""
        config = ToolConfig.objects.create(
            slug="weather-config",
            name="Weather Config",
            tool_slug="get_weather",
            parameters={}
        )
        self.assertEqual(str(config), "Weather Config")


class TestAgentConfig(TestCase):
    """Tests for the AgentConfig model."""

    @classmethod
    def setUpClass(cls):
        """Register test agent implementations before running tests."""
        super().setUpClass()
        # Register test implementations
        def my_agent_function(prompt, llm):
            return Agent(instructions=prompt)
        
        def simple_agent():
            return Agent(instructions="You are a simple assistant.")
        
        register_agent("my_agent_function", my_agent_function)
        register_agent("simple_agent", simple_agent)

    def test_create_agent_config(self):
        """Test creating an AgentConfig instance."""
        config = AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="my_agent_function",
            parameters={"prompt": "test-prompt", "llm": "openai"}
        )
        self.assertEqual(config.slug, "test-agent")
        self.assertEqual(config.name, "Test Agent")
        self.assertEqual(config.implementation, "my_agent_function")
        self.assertEqual(config.parameters, {"prompt": "test-prompt", "llm": "openai"})

    def test_agent_config_str(self):
        """Test AgentConfig string representation."""
        config = AgentConfig.objects.create(
            slug="simple-agent",
            name="Simple Agent",
            implementation="simple_agent",
            parameters={}
        )
        self.assertEqual(str(config), "Simple Agent")


class TestCollection(TestCase):
    """Tests for the Collection model (ensure slug field exists)."""

    def test_collection_has_slug(self):
        """Test that Collection has a slug field."""
        collection = Collection.objects.create(
            slug="test-collection",
            name="Test Collection",
            description="A test collection"
        )
        self.assertEqual(collection.slug, "test-collection")
        self.assertEqual(collection.name, "Test Collection")
