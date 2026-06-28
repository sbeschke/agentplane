"""Tests for the resolver module."""

from django.test import TestCase
from pydantic_ai import Agent, Tool as PydanticTool
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.resolver import resolve_dependency, get_agent, validate_agent_config
from mops.registry import register_agent, register_tool_factory
from mops.resolver import DependencyNotFoundError, InvalidTypeError


class TestResolveDependency(TestCase):
    """Tests for the resolve_dependency function."""

    def test_resolve_prompt(self):
        """Test resolving a Prompt by slug."""
        Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")
        result = resolve_dependency(Prompt, "test-prompt")
        self.assertEqual(result.slug, "test-prompt")
        self.assertEqual(result.text, "Hello")

    def test_resolve_llm_provider(self):
        """Test resolving an LLMProvider by slug."""
        LLMProvider.objects.create(
            slug="test-provider",
            name="Test",
            url="http://test.com",
            default_model="gpt-4",
        )
        result = resolve_dependency(LLMProvider, "test-provider")
        self.assertEqual(result.slug, "test-provider")
        self.assertEqual(result.default_model, "gpt-4")

    def test_resolve_collection(self):
        """Test resolving a Collection by slug."""
        Collection.objects.create(slug="test-collection", name="Test")
        result = resolve_dependency(Collection, "test-collection")
        self.assertEqual(result.slug, "test-collection")

    def test_resolve_list_of_collections(self):
        """Test resolving a list of Collections by slugs."""
        Collection.objects.create(slug="c1", name="C1")
        Collection.objects.create(slug="c2", name="C2")
        result = resolve_dependency(list[Collection], ["c1", "c2"])
        self.assertEqual(len(result), 2)
        self.assertEqual(set(r.slug for r in result), {"c1", "c2"})

    def test_resolve_nonexistent_prompt(self):
        """Test resolving a non-existent Prompt raises DependencyNotFoundError."""
        with self.assertRaises(DependencyNotFoundError):
            resolve_dependency(Prompt, "nonexistent")

    def test_resolve_none_for_optional(self):
        """Test resolving None for an Optional parameter."""
        result = resolve_dependency(Prompt | None, None)
        self.assertIsNone(result)

    def test_resolve_none_for_non_optional(self):
        """Test resolving None for a non-optional parameter raises InvalidTypeError."""
        with self.assertRaises(InvalidTypeError):
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
        Collection.objects.create(slug="c1", name="C1")
        ToolConfig.objects.create(
            slug="search-config",
            name="Search Config",
            tool_slug="search_documents",
            parameters={"collections": ["c1"]},
        )

        result = resolve_dependency(PydanticTool, "search-config")
        self.assertIsInstance(result, PydanticTool)

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

        result = resolve_dependency(
            list[PydanticTool], ["tool-config-1", "tool-config-2"]
        )
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(t, PydanticTool) for t in result))


class TestGetAgent(TestCase):
    """Tests for the get_agent function."""

    def test_get_agent_success(self):
        """Test getting an agent by slug."""
        Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=[prompt.text])

        register_agent("test_agent", test_agent)

        AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt"},
        )

        agent = get_agent("test-agent")
        self.assertEqual(agent._instructions, "Hello")

    def test_get_agent_with_optional_param(self):
        """Test getting an agent with optional parameters."""
        Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        def test_agent(prompt: Prompt, llm: LLMProvider | None = None) -> Agent:
            return Agent(instructions=[prompt.text])

        register_agent("test_agent_optional", test_agent)

        AgentConfig.objects.create(
            slug="test-agent-optional",
            name="Test Agent Optional",
            implementation="test_agent_optional",
            parameters={"prompt": "test-prompt"},  # llm is optional
        )

        agent = get_agent("test-agent-optional")
        self.assertEqual(agent._instructions, "Hello")

    def test_get_agent_nonexistent_config(self):
        """Test getting a non-existent agent config raises error."""
        with self.assertRaises(DependencyNotFoundError):
            get_agent("nonexistent")


class TestValidateAgentConfig(TestCase):
    """Tests for the validate_agent_config function."""

    def test_valid_config(self):
        """Test validating a valid AgentConfig."""

        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=[prompt.text])

        register_agent("valid_agent", test_agent)

        config = AgentConfig(
            slug="test-agent",
            implementation="valid_agent",
            parameters={"prompt": "test-prompt"},
        )
        errors = validate_agent_config(config)
        self.assertEqual(errors, [])

    def test_missing_required_parameter(self):
        """Test validating a config with missing required parameter."""

        def test_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
            return Agent(instructions=[prompt.text])

        register_agent("missing_param_agent", test_agent)

        config = AgentConfig(
            slug="test-agent",
            implementation="missing_param_agent",
            parameters={"prompt": "test-prompt"},  # Missing llm
        )
        errors = validate_agent_config(config)
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required parameter 'llm'", errors[0])

    def test_extra_parameter(self):
        """Test validating a config with extra parameter."""

        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=[prompt.text])

        register_agent("extra_param_agent", test_agent)

        config = AgentConfig(
            slug="test-agent",
            implementation="extra_param_agent",
            parameters={"prompt": "test-prompt", "extra": "value"},
        )
        errors = validate_agent_config(config)
        self.assertEqual(len(errors), 1)
        self.assertIn("Extra parameter 'extra'", errors[0])

    def test_nonexistent_implementation(self):
        """Test validating a config with non-existent implementation."""
        config = AgentConfig(
            slug="test-agent", implementation="nonexistent_agent", parameters={}
        )
        errors = validate_agent_config(config)
        self.assertEqual(len(errors), 1)
        self.assertIn("not registered", errors[0])

    def test_optional_parameter_with_none(self):
        """Test validating a config with optional parameter set to None."""

        def test_agent(prompt: Prompt, llm: LLMProvider | None = None) -> Agent:
            return Agent(instructions=[prompt.text])

        register_agent("optional_none_agent", test_agent)

        config = AgentConfig(
            slug="test-agent",
            implementation="optional_none_agent",
            parameters={"prompt": "test-prompt", "llm": None},
        )
        errors = validate_agent_config(config)
        self.assertEqual(errors, [])

    def test_list_parameter_validation(self):
        """Test validating a config with list parameter."""

        def test_agent(collections: list[Collection]) -> Agent:
            return Agent(instructions="test")

        register_agent("list_param_agent", test_agent)

        config = AgentConfig(
            slug="test-agent",
            implementation="list_param_agent",
            parameters={"collections": ["c1", "c2"]},  # Valid list
        )
        errors = validate_agent_config(config)
        self.assertEqual(errors, [])

    def test_list_parameter_with_non_list_value(self):
        """Test validating a config with list parameter but non-list value."""

        def test_agent(collections: list[Collection]) -> Agent:
            return Agent(instructions="test")

        register_agent("invalid_list_agent", test_agent)

        config = AgentConfig(
            slug="test-agent",
            implementation="invalid_list_agent",
            parameters={"collections": "not-a-list"},  # Invalid
        )
        errors = validate_agent_config(config)
        self.assertEqual(len(errors), 1)
        self.assertIn("expects list", errors[0])
