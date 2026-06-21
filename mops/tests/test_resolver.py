"""Tests for the resolver module."""

import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.resolver import resolve_dependency, get_agent, validate_agent_config
from mops.registry import register_agent, register_tool_factory
from mops.resolver import DependencyNotFoundError, InvalidTypeError


@pytest.mark.django_db
class TestResolveDependency:
    """Tests for the resolve_dependency function."""

    def test_resolve_prompt(self):
        """Test resolving a Prompt by slug."""
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")
        result = resolve_dependency(Prompt, "test-prompt")
        assert result.slug == "test-prompt"
        assert result.text == "Hello"

    def test_resolve_llm_provider(self):
        """Test resolving an LLMProvider by slug."""
        provider = LLMProvider.objects.create(
            slug="test-provider",
            name="Test",
            url="http://test.com",
            default_model="gpt-4"
        )
        result = resolve_dependency(LLMProvider, "test-provider")
        assert result.slug == "test-provider"
        assert result.default_model == "gpt-4"

    def test_resolve_collection(self):
        """Test resolving a Collection by slug."""
        collection = Collection.objects.create(slug="test-collection", name="Test")
        result = resolve_dependency(Collection, "test-collection")
        assert result.slug == "test-collection"

    def test_resolve_list_of_collections(self):
        """Test resolving a list of Collections by slugs."""
        c1 = Collection.objects.create(slug="c1", name="C1")
        c2 = Collection.objects.create(slug="c2", name="C2")
        result = resolve_dependency(list[Collection], ["c1", "c2"])
        assert len(result) == 2
        assert set(r.slug for r in result) == {"c1", "c2"}

    def test_resolve_nonexistent_prompt(self):
        """Test resolving a non-existent Prompt raises DependencyNotFoundError."""
        with pytest.raises(DependencyNotFoundError):
            resolve_dependency(Prompt, "nonexistent")

    def test_resolve_none_for_optional(self):
        """Test resolving None for an Optional parameter."""
        result = resolve_dependency(Prompt | None, None)
        assert result is None

    def test_resolve_none_for_non_optional(self):
        """Test resolving None for a non-optional parameter raises InvalidTypeError."""
        with pytest.raises(InvalidTypeError):
            resolve_dependency(Prompt, None)

    def test_resolve_tool_config(self):
        """Test resolving a ToolConfig to a PydanticTool."""
        # Register a tool factory
        def search_tool_factory(collections: list[Collection], **kwargs):
            def search(query: str) -> str:
                return "results"
            return PydanticTool(search)

        register_tool_factory("search_documents", search_tool_factory)

        # Create ToolConfig
        c1 = Collection.objects.create(slug="c1", name="C1")
        ToolConfig.objects.create(
            slug="search-config",
            name="Search Config",
            tool_slug="search_documents",
            parameters={"collections": ["c1"]}
        )

        result = resolve_dependency(PydanticTool, "search-config")
        assert isinstance(result, PydanticTool)

    def test_resolve_list_of_tool_configs(self):
        """Test resolving a list of ToolConfigs to PydanticTools."""
        def tool_factory(**kwargs):
            def tool(x: int) -> int:
                return x * 2
            return PydanticTool(tool)

        register_tool_factory("tool1", tool_factory)
        register_tool_factory("tool2", tool_factory)

        ToolConfig.objects.create(
            slug="tool-config-1", tool_slug="tool1", parameters={}
        )
        ToolConfig.objects.create(
            slug="tool-config-2", tool_slug="tool2", parameters={}
        )

        result = resolve_dependency(list[PydanticTool], ["tool-config-1", "tool-config-2"])
        assert len(result) == 2
        assert all(isinstance(t, PydanticTool) for t in result)


@pytest.mark.django_db
class TestGetAgent:
    """Tests for the get_agent function."""

    def test_get_agent_success(self):
        """Test getting an agent by slug."""
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        @register_agent("test_agent", lambda: None)
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt"}
        )

        agent = get_agent("test-agent")
        assert agent.instructions == "Hello"

    def test_get_agent_with_optional_param(self):
        """Test getting an agent with optional parameters."""
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        @register_agent("test_agent_optional", lambda: None)
        def test_agent(prompt: Prompt, llm: LLMProvider | None = None) -> Agent:
            return Agent(instructions=prompt.text)

        AgentConfig.objects.create(
            slug="test-agent-optional",
            name="Test Agent Optional",
            implementation="test_agent_optional",
            parameters={"prompt": "test-prompt"}  # llm is optional
        )

        agent = get_agent("test-agent-optional")
        assert agent.instructions == "Hello"

    def test_get_agent_nonexistent_config(self):
        """Test getting a non-existent agent config raises error."""
        with pytest.raises(AgentConfig.DoesNotExist):
            get_agent("nonexistent")


@pytest.mark.django_db
class TestValidateAgentConfig:
    """Tests for the validate_agent_config function."""

    def test_valid_config(self):
        """Test validating a valid AgentConfig."""
        @register_agent("valid_agent", lambda: None)
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="valid_agent",
            parameters={"prompt": "test-prompt"}
        )
        errors = validate_agent_config(config)
        assert errors == []

    def test_missing_required_parameter(self):
        """Test validating a config with missing required parameter."""
        @register_agent("missing_param_agent", lambda: None)
        def test_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="missing_param_agent",
            parameters={"prompt": "test-prompt"}  # Missing llm
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "Missing required parameter 'llm'" in errors[0]

    def test_extra_parameter(self):
        """Test validating a config with extra parameter."""
        @register_agent("extra_param_agent", lambda: None)
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="extra_param_agent",
            parameters={"prompt": "test-prompt", "extra": "value"}
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "Extra parameter 'extra'" in errors[0]

    def test_nonexistent_implementation(self):
        """Test validating a config with non-existent implementation."""
        config = AgentConfig(
            slug="test-agent",
            implementation="nonexistent_agent",
            parameters={}
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "not registered" in errors[0]

    def test_optional_parameter_with_none(self):
        """Test validating a config with optional parameter set to None."""
        @register_agent("optional_none_agent", lambda: None)
        def test_agent(prompt: Prompt, llm: LLMProvider | None = None) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="optional_none_agent",
            parameters={"prompt": "test-prompt", "llm": None}
        )
        errors = validate_agent_config(config)
        assert errors == []

    def test_list_parameter_validation(self):
        """Test validating a config with list parameter."""
        @register_agent("list_param_agent", lambda: None)
        def test_agent(collections: list[Collection]) -> Agent:
            return Agent(instructions="test")

        config = AgentConfig(
            slug="test-agent",
            implementation="list_param_agent",
            parameters={"collections": ["c1", "c2"]}  # Valid list
        )
        errors = validate_agent_config(config)
        assert errors == []

    def test_list_parameter_with_non_list_value(self):
        """Test validating a config with list parameter but non-list value."""
        @register_agent("invalid_list_agent", lambda: None)
        def test_agent(collections: list[Collection]) -> Agent:
            return Agent(instructions="test")

        config = AgentConfig(
            slug="test-agent",
            implementation="invalid_list_agent",
            parameters={"collections": "not-a-list"}  # Invalid
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "expects list" in errors[0]
