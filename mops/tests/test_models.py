"""Tests for the new code-defined agent models."""

import pytest
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig


@pytest.mark.django_db
class TestPrompt:
    """Tests for the Prompt model."""

    def test_create_prompt(self):
        """Test creating a Prompt instance."""
        prompt = Prompt.objects.create(
            slug="test-prompt",
            name="Test Prompt",
            text="You are a helpful assistant.",
            description="A test prompt"
        )
        assert prompt.slug == "test-prompt"
        assert prompt.name == "Test Prompt"
        assert prompt.text == "You are a helpful assistant."
        assert prompt.description == "A test prompt"

    def test_prompt_str(self):
        """Test Prompt string representation."""
        prompt = Prompt.objects.create(
            slug="test-prompt",
            name="Test Prompt",
            text="Hello"
        )
        assert str(prompt) == "Test Prompt"


@pytest.mark.django_db
class TestLLMProvider:
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
        assert provider.slug == "openai"
        assert provider.name == "OpenAI"
        assert provider.default_model == "gpt-4"
        assert provider.available_models == ["gpt-4", "gpt-3.5-turbo"]

    def test_provider_str(self):
        """Test LLMProvider string representation."""
        provider = LLMProvider.objects.create(
            slug="local",
            name="Local LLM",
            url="http://localhost:8000/v1"
        )
        assert str(provider) == "Local LLM"


@pytest.mark.django_db
class TestToolConfig:
    """Tests for the ToolConfig model."""

    def test_create_tool_config(self):
        """Test creating a ToolConfig instance."""
        config = ToolConfig.objects.create(
            slug="search-config",
            name="Search Config",
            tool_slug="search_documents",
            parameters={"collections": ["docs", "manuals"]}
        )
        assert config.slug == "search-config"
        assert config.name == "Search Config"
        assert config.tool_slug == "search_documents"
        assert config.parameters == {"collections": ["docs", "manuals"]}

    def test_tool_config_str(self):
        """Test ToolConfig string representation."""
        config = ToolConfig.objects.create(
            slug="weather-config",
            name="Weather Config",
            tool_slug="get_weather",
            parameters={}
        )
        assert str(config) == "Weather Config"


@pytest.mark.django_db
class TestAgentConfig:
    """Tests for the AgentConfig model."""

    def test_create_agent_config(self):
        """Test creating an AgentConfig instance."""
        config = AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="my_agent_function",
            parameters={"prompt": "test-prompt", "llm": "openai"}
        )
        assert config.slug == "test-agent"
        assert config.name == "Test Agent"
        assert config.implementation == "my_agent_function"
        assert config.parameters == {"prompt": "test-prompt", "llm": "openai"}

    def test_agent_config_str(self):
        """Test AgentConfig string representation."""
        config = AgentConfig.objects.create(
            slug="simple-agent",
            name="Simple Agent",
            implementation="simple_agent",
            parameters={}
        )
        assert str(config) == "Simple Agent"


@pytest.mark.django_db
class TestCollection:
    """Tests for the Collection model (ensure slug field exists)."""

    def test_collection_has_slug(self):
        """Test that Collection has a slug field."""
        collection = Collection.objects.create(
            slug="test-collection",
            name="Test Collection",
            description="A test collection"
        )
        assert collection.slug == "test-collection"
        assert collection.name == "Test Collection"
