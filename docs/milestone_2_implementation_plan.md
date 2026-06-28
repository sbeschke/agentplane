# Milestone 2 Implementation Plan - Code-Defined Agents

## Overview

This document outlines the step-by-step implementation plan for Milestone 2: Code-Defined Agents.
The milestone introduces a clean separation between agent code (implementations, tools) and configuration (prompts, providers, collections, tool configs).

**Target State:** 
- Developers write `@agent` decorated functions that receive dependencies (Prompt, LLMProvider, Collection, ToolConfig) and return PydanticAI `Agent` objects.
- Configuration is stored in DB models (`Prompt`, `LLMProvider`, `Collection`, `ToolConfig`) and wired via `AgentConfig`.
- Tools are registered as **factories** via `@tool`. Parameterized tools are configured via `ToolConfig` instances.

---

## Phases

### Phase 1: Foundation (Models + Registry)
*Prerequisite for all other work. No breaking changes yet.*

### Phase 2: Agent Code (Decorators + Resolver)
*Enables writing agent functions. Still no breaking changes.*

### Phase 3: Migration (Data)
*Migrates existing Agent model to Prompt + AgentConfig. Introduces breaking changes, requires data migration.*

### Phase 4: Integration (Endpoints + Tools + Validation)
*Connects everything to the API and adds built-in tools.*

### Phase 5: Quality (Tests + Example App)
*Ensures reliability and demonstrates usage.*

---

## Detailed Tasks

### Phase 1: Foundation

#### 1.1 Add new models
**Files:** `mops/models.py`

- [ ] Create `Prompt` model (migrated fields from Agent: `name`, `slug`, `description`, `instructions` → `text`)
  ```python
  class Prompt(models.Model):
      slug = models.SlugField(unique=True)
      name = models.CharField(max_length=255)
      text = models.TextField()
      description = models.TextField(blank=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
  ```

- [ ] Add `slug` field to `LLMProvider` (currently missing)
  ```python
  class LLMProvider(models.Model):
      slug = models.SlugField(unique=True)  # NEW
      name = models.CharField(max_length=255)
      url = models.URLField(...)
      available_models = models.JSONField(default=list)
      default_model = models.CharField(max_length=255, blank=True)  # NEW: default model for this provider
      last_discovered = models.DateTimeField(null=True, blank=True)
  ```

- [ ] Create `ToolConfig` model (NEW: for parameterized tools)
  ```python
  class ToolConfig(models.Model):
      slug = models.SlugField(unique=True)
      name = models.CharField(max_length=255)
      tool_slug = models.CharField(max_length=255)  # registered tool factory name (e.g., "search_documents")
      parameters = models.JSONField(default=dict)  # runtime parameters for the tool factory (e.g., {"collections": ["docs"]})
      description = models.TextField(blank=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
  ```

- [ ] Create `AgentConfig` model
  ```python
  class AgentConfig(models.Model):
      slug = models.SlugField(unique=True)
      name = models.CharField(max_length=255)
      description = models.TextField(blank=True)
      implementation = models.CharField(max_length=255)  # registered function name
      parameters = models.JSONField(default=dict)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
  ```

- [ ] Add `slug` field to `Collection` if missing (verify current state)

- [ ] Create and run Django migration for new fields/models

#### 1.2 Create Registry
**File:** `mops/registry.py` (new)

```python
from typing import Callable
from pydantic_ai import Agent, Tool as PydanticTool

_agent_registry: dict[str, Callable] = {}
_tool_factory_registry: dict[str, Callable] = {}  # Changed: stores factories, not PydanticTool objects


def register_agent(impl_name: str, factory: Callable):
    """Register an agent factory function by implementation name."""
    _agent_registry[impl_name] = factory


def register_tool_factory(tool_slug: str, factory: Callable):
    """Register a tool factory by slug. The factory must accept **kwargs and return a PydanticTool."""
    _tool_factory_registry[tool_slug] = factory


def get_agent_factory(impl_name: str) -> Callable:
    """Get agent factory by implementation name."""
    if impl_name not in _agent_registry:
        raise KeyError(f"Agent implementation '{impl_name}' not registered")
    return _agent_registry[impl_name]


def get_tool_factory(tool_slug: str) -> Callable:
    """Get tool factory by slug."""
    if tool_slug not in _tool_factory_registry:
        raise KeyError(f"Tool factory '{tool_slug}' not registered")
    return _tool_factory_registry[tool_slug]


def list_agents() -> list[str]:
    """List all registered agent implementation names."""
    return list(_agent_registry.keys())


def list_tool_factories() -> list[str]:
    """List all registered tool factory slugs."""
    return list(_tool_factory_registry.keys())
```

---

### Phase 2: Agent Code

#### 2.1 Create Decorators
**File:** `mops/decorators.py` (new)

```python
from functools import wraps
from typing import Callable
from pydantic_ai import Tool as PydanticTool
from mops.registry import register_agent, register_tool_factory


def agent(func: Callable) -> Callable:
    """
    Register an agent factory function.
    The function must return a pydantic_ai.Agent.
    Registered by function name.
    """
    register_agent(func.__name__, func)
    return func


def tool(*, slug: str | None = None):
    """
    Decorator that registers a tool factory function.
    The factory must accept **kwargs and return a PydanticAI Tool.
    Returns the original function (not a PydanticTool).
    """
    def decorator(func: Callable):
        registry_slug = slug or func.__name__
        register_tool_factory(registry_slug, func)
        return func  # Returns the original function (factory)
    return decorator
```

#### 2.2 Create Resolver
**File:** `mops/resolver.py` (new)

```python
import inspect
from typing import get_origin, get_args, Any
from pydantic_ai import Tool as PydanticTool, Agent
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.registry import get_agent_factory, get_tool_factory

# Custom exceptions
class DependencyNotFoundError(ValueError):
    """Raised when a dependency slug is not found."""
    pass

class InvalidTypeError(ValueError):
    """Raised when a dependency type is invalid or unsupported."""
    pass


# Map of dependency types to their resolution strategies
_DB_TYPE_MAP = {
    Prompt: Prompt,
    LLMProvider: LLMProvider,
    Collection: Collection,
    ToolConfig: ToolConfig,
}


def resolve_dependency(param_type: type, slug: str | list[str] | None) -> Any:
    """
    Resolve a dependency slug (or list of slugs) to the actual object(s).

    Handles:
    - PydanticAI Tool types (instantiated from ToolConfig via tool factory)
    - DB model types (Prompt, LLMProvider, Collection, ToolConfig)
    - list[DB model] (multiple DB objects via slug__in query)
    - Optional types (e.g., Prompt | None)
    - None values (for Optional parameters)
    """
    # Handle None (for Optional parameters)
    if slug is None:
        if get_origin(param_type) is not type(None) and not (
            get_origin(param_type) is Union and type(None) in get_args(param_type)
        ):
            raise InvalidTypeError(f"Non-optional parameter {param_type} cannot be None")
        return None

    # Handle PydanticAI Tool types (resolved from ToolConfig + factory)
    if param_type is PydanticTool:
        # slug must be a ToolConfig slug
        tool_config = ToolConfig.objects.get(slug=slug)
        factory = get_tool_factory(tool_config.tool_slug)
        return factory(**tool_config.parameters)

    # Handle list types: list[ToolConfig], list[Collection], list[Prompt], list[LLMProvider]
    if get_origin(param_type) is list:
        inner_type = get_args(param_type)[0]

        # Handle list[PydanticTool]
        if inner_type is PydanticTool:
            tool_configs = ToolConfig.objects.filter(slug__in=slug)
            tools = []
            for tc in tool_configs:
                factory = get_tool_factory(tc.tool_slug)
                tools.append(factory(**tc.parameters))
            return tools

        # Handle list of DB model types
        inner_model = _DB_TYPE_MAP.get(inner_type)
        if inner_model:
            return list(inner_model.objects.filter(slug__in=slug))

        raise InvalidTypeError(f"Unknown list dependency type: {param_type}")

    # Handle DB model types
    model_class = _DB_TYPE_MAP.get(param_type)
    if model_class:
        try:
            return model_class.objects.get(slug=slug)
        except model_class.DoesNotExist:
            raise DependencyNotFoundError(f"{model_class.__name__} with slug '{slug}' not found")

    raise InvalidTypeError(f"Unknown dependency type: {param_type}")


def get_agent(slug: str) -> Agent:
    """
    Resolve an agent by its AgentConfig slug, injecting all dependencies.

    1. Load AgentConfig from DB
    2. Get factory function from registry
    3. Inspect factory signature
    4. For each parameter, resolve slug(s) to actual objects
    5. Call factory with resolved dependencies
    """
    config = AgentConfig.objects.get(slug=slug)
    factory = get_agent_factory(config.implementation)
    sig = inspect.signature(factory)

    kwargs = {}
    for param_name, param in sig.parameters.items():
        if param_name not in config.parameters:
            # Check if parameter has a default value
            if param.default is inspect.Parameter.empty:
                raise DependencyNotFoundError(
                    f"AgentConfig for '{config.slug}' missing parameter '{param_name}' "
                    f"required by implementation '{config.implementation}'"
                )
            # Use default value
            kwargs[param_name] = param.default
            continue

        param_slug = config.parameters[param_name]
        param_type = param.annotation
        kwargs[param_name] = resolve_dependency(param_type, param_slug)

    return factory(**kwargs)


def validate_agent_config(config: AgentConfig) -> list[str]:
    """
    Validate that an AgentConfig's parameters match its implementation's signature.
    Returns list of error messages, empty if valid.
    Supports Optional and list types.
    """
    errors = []
    try:
        factory = get_agent_factory(config.implementation)
    except KeyError:
        errors.append(f"Implementation '{config.implementation}' not registered")
        return errors

    sig = inspect.signature(factory)
    param_names = set(sig.parameters.keys())
    config_param_names = set(config.parameters.keys())

    # Check for missing required parameters (no default value)
    for param_name, param in sig.parameters.items():
        if param.default is inspect.Parameter.empty and param_name not in config_param_names:
            errors.append(
                f"Missing required parameter '{param_name}' in config for implementation "
                f"'{config.implementation}'"
            )

    # Check for extra parameters in config
    extra = config_param_names - param_names
    for p in extra:
        errors.append(
            f"Extra parameter '{p}' in config not used by implementation "
            f"'{config.implementation}'"
        )

    # Check parameter types (basic validation)
    for param_name, param in sig.parameters.items():
        if param_name in config.parameters:
            param_type = param.annotation
            param_slug = config.parameters[param_name]

            # Skip None checks for Optional types
            if param_slug is None:
                if get_origin(param_type) is not type(None) and not (
                    get_origin(param_type) is Union and type(None) in get_args(param_type)
                ):
                    errors.append(
                        f"Parameter '{param_name}' is None but type {param_type} is not Optional"
                    )
                continue

            # For list types, validate slug is a list
            if get_origin(param_type) is list:
                if not isinstance(param_slug, list):
                    errors.append(
                        f"Parameter '{param_name}' expects list but got {type(param_slug).__name__}"
                    )

    return errors
```

---

### Phase 3: Migration

#### 3.1 Create new models in DB
- [ ] Run migration from Phase 1.1 to create Prompt, ToolConfig, update LLMProvider, create AgentConfig

#### 3.2 Create data migration
**File:** `mops/migrations/00XX_migrate_to_code_defined.py`

```python
from django.db import migrations


def migrate_agent_to_prompt_and_config(apps, schema_editor):
    """Migrate existing Agent instances to Prompt + AgentConfig."""
    Agent = apps.get_model("mops", "Agent")
    Prompt = apps.get_model("mops", "Prompt")
    AgentConfig = apps.get_model("mops", "AgentConfig")
    LLMProvider = apps.get_model("mops", "LLMProvider")

    for agent in Agent.objects.all():
        # Create Prompt from Agent
        prompt_slug = agent.slug or f"prompt-{agent.id}"
        prompt = Prompt.objects.create(
            slug=prompt_slug,
            name=agent.name,
            text=agent.instructions or "",
            description=agent.description or "",
        )

        # Create AgentConfig
        config_slug = agent.slug or f"config-{agent.id}"
        params = {"prompt": prompt_slug}

        if agent.llm_provider:
            params["llm"] = agent.llm_provider.slug

        # Handle search_enabled and allowed_collections
        # For migrated agents, we'll use the legacy_agent implementation
        # which expects collections as a list
        if agent.search_enabled and agent.allowed_collections.exists():
            params["collections"] = [c.slug for c in agent.allowed_collections.all()]

        AgentConfig.objects.create(
            slug=config_slug,
            name=agent.name,
            description=agent.description or "",
            implementation="legacy_agent",
            parameters=params,
        )


class Migration(migrations.Migration):
    dependencies = [
        # Add dependencies on previous migrations
        ("mops", "00XX_previous_migration"),
    ]

    operations = [
        migrations.RunPython(migrate_agent_to_prompt_and_config, migrations.RunPython.noop),
    ]
```

#### 3.3 Update Conversation model
**File:** `mops/models.py`

Change:
```python
# OLD
agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="conversations")

# NEW
agent_config = models.ForeignKey(
    AgentConfig,
    on_delete=models.CASCADE,
    related_name="conversations",
)
```

Create migration for this change.

#### 3.4 Create legacy agent wrapper
**File:** `mops/agents.py` (new)

```python
"""Built-in agent implementations."""
from pydantic_ai import Agent
from mops import agent
from mops.models import Prompt, LLMProvider, Collection


@agent
def legacy_agent(
    prompt: Prompt,
    llm: LLMProvider | None = None,
    collections: list[Collection] | None = None,
) -> Agent:
    """
    Legacy agent wrapper that mimics the old Agent model behavior.
    Used during migration from the old Agent model.
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
        # Note: This requires ToolConfig to be set up, but for legacy purposes
        # we'll create the tool directly here
        tools.append(search_documents_tool_factory(collections=collections))

    return Agent(
        instructions=prompt.text,
        tools=tools,
        **model_config
    )
```

---

### Phase 4: Integration

#### 4.1 Create built-in tools
**File:** `mops/tools.py` (new)

```python
"""Built-in tools for agents."""
from typing import Union
from pydantic_ai import Tool as PydanticTool
from mops import tool
from mops.models import Collection


@tool(slug="search_documents")
def search_documents_tool_factory(collections: list[Collection]) -> PydanticTool:
    """
    Factory for a document search tool.
    Creates a PydanticAI Tool that searches across the configured collections.
    
    Args:
        collections: List of Collection objects to search in.
    
    Returns:
        A PydanticAI Tool that can be used by agents.
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


@tool(slug="get_weather")
def get_weather_tool_factory() -> PydanticTool:
    """
    Factory for a weather tool (example stateless tool).
    Returns a PydanticAI Tool that doesn't require runtime configuration.
    """
    def get_weather(city: str) -> str:
        """Get weather information for a city."""
        # In a real app, this would call a weather API
        return f"The weather in {city} is sunny and 72°F."

    return PydanticTool(get_weather)
```

Verify `vector_store.py` exists and has `search_similar` function. If not, create it:

**File:** `mops/vector_store.py` (verify/create)
```python
from django.db.models import Q
from mops.models import DocumentChunk


def search_similar(collection, query: str, k: int = 3, embedding_func=None):
    """
    Search for similar document chunks in a collection.

    Args:
        collection: Collection instance
        query: Search query text
        k: Number of results to return
        embedding_func: Function to generate embeddings (injected for testing)

    Returns:
        QuerySet of DocumentChunk objects, ordered by similarity
    """
    if embedding_func is None:
        from mops.embeddings import embed_text
        embedding_func = embed_text

    query_embedding = embedding_func(query)

    return (
        DocumentChunk.objects
        .filter(document__collection=collection)
        .order_by("embedding <-> %s")[:k]
    )
```

#### 4.2 Create agent endpoints
**File:** `mops/endpoints.py` (new)

```python
from ninja import Router
from pydantic_ai import Agent
from mops.resolver import get_agent
from mops.models import AgentConfig


def create_agent_router(slug: str) -> Router:
    """Create a router for a specific agent."""
    router = Router()

    @router.post("/")
    def run_agent(request, message: str):
        """Run the agent with a message."""
        agent = get_agent(slug)
        # Synchronous response (streaming scoped out)
        result = agent.run(message)
        return {"response": str(result)}

    @router.get("/")
    def get_agent_info(request):
        """Get agent configuration info."""
        config = AgentConfig.objects.get(slug=slug)
        return {
            "slug": config.slug,
            "name": config.name,
            "description": config.description,
            "implementation": config.implementation,
        }

    return router
```

#### 4.3 Update API URLs
**File:** `mops/urls.py`

```python
from ninja import NinjaAPI
from mops.models import AgentConfig
from mops.endpoints import create_agent_router

api = NinjaAPI()


def register_agent_routes():
    """Register routes for all AgentConfig instances."""
    for config in AgentConfig.objects.all():
        router = create_agent_router(config.slug)
        api.add_router(f"/agents/{config.slug}/", router)


@api.get("/agents/")
def list_agents(request):
    """List all available agents."""
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "implementation": c.implementation,
        }
        for c in AgentConfig.objects.all()
    ]
```

**File:** `mops/apps.py`
```python
from django.apps import AppConfig


class MopsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mops"

    def ready(self):
        # Register agent routes on startup
        from mops.urls import register_agent_routes
        register_agent_routes()

        # Import signals to register them
        from mops import signals  # noqa: F401
```

#### 4.4 Add validation signals
**File:** `mops/signals.py` (new)

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver
from mops.models import AgentConfig
from mops.resolver import validate_agent_config, InvalidTypeError, DependencyNotFoundError


@receiver(pre_save, sender=AgentConfig)
def validate_agent_config_on_save(sender, instance, **kwargs):
    """Validate AgentConfig before saving."""
    errors = validate_agent_config(instance)
    if errors:
        raise ValueError("; ".join(errors))
```

---

### Phase 5: Quality

#### 5.1 Unit Tests
**File:** `tests/test_registry.py`

```python
import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import (
    register_agent, register_tool_factory, get_agent_factory, get_tool_factory,
    list_agents, list_tool_factories
)


def test_agent_registration():
    def my_agent(prompt):
        return Agent(instructions=prompt)

    register_agent("my_agent", my_agent)
    assert "my_agent" in list_agents()
    assert get_agent_factory("my_agent") is my_agent


def test_tool_factory_registration():
    def my_tool_factory(**kwargs):
        def my_tool(x: int) -> int:
            return x * 2
        return PydanticTool(my_tool)

    register_tool_factory("my_tool", my_tool_factory)
    assert "my_tool" in list_tool_factories()
    assert get_tool_factory("my_tool") is my_tool_factory


def test_get_nonexistent_agent():
    with pytest.raises(KeyError):
        get_agent_factory("nonexistent")


def test_get_nonexistent_tool_factory():
    with pytest.raises(KeyError):
        get_tool_factory("nonexistent")
```

**File:** `tests/test_resolver.py`

```python
import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.resolver import resolve_dependency, get_agent, validate_agent_config
from mops.registry import register_agent, register_tool_factory
from mops.resolver import DependencyNotFoundError, InvalidTypeError


@pytest.mark.django_db
class TestResolveDependency:
    def test_resolve_prompt(self):
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")
        result = resolve_dependency(Prompt, "test-prompt")
        assert result.slug == "test-prompt"

    def test_resolve_llm_provider(self):
        provider = LLMProvider.objects.create(
            slug="test-provider", name="Test", url="http://test.com", default_model="gpt-4"
        )
        result = resolve_dependency(LLMProvider, "test-provider")
        assert result.slug == "test-provider"

    def test_resolve_collection(self):
        collection = Collection.objects.create(slug="test-collection", name="Test")
        result = resolve_dependency(Collection, "test-collection")
        assert result.slug == "test-collection"

    def test_resolve_list_of_collections(self):
        c1 = Collection.objects.create(slug="c1", name="C1")
        c2 = Collection.objects.create(slug="c2", name="C2")
        result = resolve_dependency(list[Collection], ["c1", "c2"])
        assert len(result) == 2
        assert set(r.slug for r in result) == {"c1", "c2"}

    def test_resolve_tool_config(self):
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

    def test_resolve_nonexistent_prompt(self):
        with pytest.raises(DependencyNotFoundError):
            resolve_dependency(Prompt, "nonexistent")

    def test_resolve_none_for_optional(self):
        # Optional[Prompt] should accept None
        result = resolve_dependency(Prompt | None, None)
        assert result is None

    def test_resolve_none_for_non_optional(self):
        with pytest.raises(InvalidTypeError):
            resolve_dependency(Prompt, None)


@pytest.mark.django_db
class TestGetAgent:
    def test_get_agent_success(self):
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        @agent
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
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        @agent
        def test_agent(prompt: Prompt, llm: LLMProvider | None = None) -> Agent:
            return Agent(instructions=prompt.text)

        AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt"}  # llm is optional
        )

        agent = get_agent("test-agent")
        assert agent.instructions == "Hello"

    def test_get_agent_nonexistent_config(self):
        with pytest.raises(AgentConfig.DoesNotExist):
            get_agent("nonexistent")


@pytest.mark.django_db
class TestValidateAgentConfig:
    def test_valid_config(self):
        @agent
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt"}
        )
        errors = validate_agent_config(config)
        assert errors == []

    def test_missing_required_parameter(self):
        @agent
        def test_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt"}  # Missing llm
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "Missing required parameter 'llm'" in errors[0]

    def test_extra_parameter(self):
        @agent
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt", "extra": "value"}
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "Extra parameter 'extra'" in errors[0]

    def test_nonexistent_implementation(self):
        config = AgentConfig(
            slug="test-agent",
            implementation="nonexistent_agent",
            parameters={}
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "not registered" in errors[0]

    def test_optional_parameter_with_none(self):
        @agent
        def test_agent(prompt: Prompt, llm: LLMProvider | None = None) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig(
            slug="test-agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt", "llm": None}
        )
        errors = validate_agent_config(config)
        assert errors == []

    def test_list_parameter_validation(self):
        @agent
        def test_agent(collections: list[Collection]) -> Agent:
            return Agent(instructions="test")

        config = AgentConfig(
            slug="test-agent",
            implementation="test_agent",
            parameters={"collections": ["c1", "c2"]}  # Valid list
        )
        errors = validate_agent_config(config)
        assert errors == []

    def test_list_parameter_with_non_list_value(self):
        @agent
        def test_agent(collections: list[Collection]) -> Agent:
            return Agent(instructions="test")

        config = AgentConfig(
            slug="test-agent",
            implementation="test_agent",
            parameters={"collections": "not-a-list"}  # Invalid
        )
        errors = validate_agent_config(config)
        assert len(errors) == 1
        assert "expects list" in errors[0]
```

**File:** `tests/test_decorators.py`

```python
import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import list_agents, list_tool_factories, get_agent_factory, get_tool_factory
from mops.decorators import agent, tool


class TestAgentDecorator:
    def test_agent_decorator_registers_function(self):
        @agent
        def my_agent(prompt) -> Agent:
            return Agent(instructions="test")

        assert "my_agent" in list_agents()
        assert get_agent_factory("my_agent") is my_agent

    def test_agent_decorator_returns_function(self):
        @agent
        def my_agent(prompt) -> Agent:
            return Agent(instructions="test")

        assert callable(my_agent)


class TestToolDecorator:
    def test_tool_decorator_registers_factory(self):
        @tool
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        assert "my_tool_factory" in list_tool_factories()
        assert get_tool_factory("my_tool_factory") is my_tool_factory

    def test_tool_decorator_returns_original_function(self):
        @tool
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        # Should return the original factory function
        assert callable(my_tool_factory)

    def test_tool_decorator_with_custom_slug(self):
        @tool(slug="custom_slug")
        def my_tool_factory(**kwargs):
            def my_tool(x: int) -> int:
                return x * 2
            return PydanticTool(my_tool)

        assert "custom_slug" in list_tool_factories()
        assert get_tool_factory("custom_slug") is my_tool_factory
```

**File:** `tests/test_models.py`

```python
import pytest
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig


@pytest.mark.django_db
class TestPrompt:
    def test_create_prompt(self):
        prompt = Prompt.objects.create(
            slug="test-prompt",
            name="Test Prompt",
            text="You are a helpful assistant.",
            description="A test prompt"
        )
        assert prompt.slug == "test-prompt"
        assert prompt.text == "You are a helpful assistant."


@pytest.mark.django_db
class TestLLMProvider:
    def test_create_provider_with_slug_and_default_model(self):
        provider = LLMProvider.objects.create(
            slug="openai",
            name="OpenAI",
            url="https://api.openai.com/v1",
            available_models=["gpt-4", "gpt-3.5-turbo"],
            default_model="gpt-4"
        )
        assert provider.slug == "openai"
        assert provider.default_model == "gpt-4"


@pytest.mark.django_db
class TestToolConfig:
    def test_create_tool_config(self):
        config = ToolConfig.objects.create(
            slug="search-config",
            name="Search Config",
            tool_slug="search_documents",
            parameters={"collections": ["docs", "manuals"]}
        )
        assert config.slug == "search-config"
        assert config.tool_slug == "search_documents"
        assert config.parameters == {"collections": ["docs", "manuals"]}


@pytest.mark.django_db
class TestAgentConfig:
    def test_create_agent_config(self):
        config = AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="my_agent_function",
            parameters={"prompt": "test-prompt", "llm": "openai"}
        )
        assert config.slug == "test-agent"
        assert config.parameters == {"prompt": "test-prompt", "llm": "openai"}
```

**File:** `tests/test_endpoints.py`

```python
import pytest
from django.test import Client
from mops.models import Prompt, AgentConfig, ToolConfig, Collection
from mops.registry import register_agent, register_tool_factory
from pydantic_ai import Agent, Tool as PydanticTool


@pytest.mark.django_db
class TestAgentEndpoints:
    def test_list_agents_empty(self):
        client = Client()
        response = client.get("/api/agents/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_agents_with_configs(self):
        AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent",
            parameters={}
        )

        client = Client()
        response = client.get("/api/agents/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["slug"] == "test-agent"

    def test_run_agent(self):
        @register_agent("test_agent_impl", lambda: Agent(instructions="test"))
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")
        AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent_impl",
            parameters={"prompt": "test-prompt"}
        )

        client = Client()
        response = client.post("/api/agents/test-agent/", {"message": "Hi"}, content_type="application/json")
        assert response.status_code == 200
        assert "response" in response.json()

    def test_get_agent_info(self):
        AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent",
            parameters={},
            description="A test agent"
        )

        client = Client()
        response = client.get("/api/agents/test-agent/")
        assert response.status_code == 200
        assert response.json()["slug"] == "test-agent"
        assert response.json()["name"] == "Test Agent"
        assert response.json()["description"] == "A test agent"
```

#### 5.2 Example App
**Directory:** `/examples/mops-example/` (standalone project)

**Note:** Ensure the example project's `pyproject.toml` or `requirements.txt` does not conflict with the top-level `uv` config. Use relative paths or independent dependency management.

**File:** `examples/mops-example/agents.py`

```python
"""
Example agents for django-mops.
Demonstrates code-defined agent patterns.
"""
from pydantic_ai import Agent, Tool as PydanticTool
from mops import agent, tool
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
```

**File:** `examples/mops-example/fixtures/agents.yaml`

```yaml
- model: mops.Prompt
  pk: 1
  fields:
    slug: simple-prompt
    name: Simple Prompt
    text: You are a helpful assistant. Answer questions directly.
    description: Basic prompt for simple agent
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.Prompt
  pk: 2
  fields:
    slug: weather-prompt
    name: Weather Prompt
    text: You are a weather assistant. Use the get_weather tool to answer weather questions.
    description: Prompt for weather agent
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.Prompt
  pk: 3
  fields:
    slug: rag-prompt
    name: RAG Prompt
    text: You are a documentation assistant. Use the search_documents tool to find relevant information.
    description: Prompt for RAG agent
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.LLMProvider
  pk: 1
  fields:
    slug: local
    name: Local LLM
    url: http://127.0.0.1:8765/v1
    available_models: ["mistral:7b"]
    default_model: mistral:7b
    last_discovered: null

- model: mops.LLMProvider
  pk: 2
  fields:
    slug: openai
    name: OpenAI
    url: https://api.openai.com/v1
    available_models: ["gpt-4", "gpt-3.5-turbo"]
    default_model: gpt-4
    last_discovered: null

- model: mops.Collection
  pk: 1
  fields:
    slug: docs
    name: Documentation
    description: Product documentation
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.Collection
  pk: 2
  fields:
    slug: manuals
    name: Manuals
    description: User manuals
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.ToolConfig
  pk: 1
  fields:
    slug: weather-tool
    name: Weather Tool
    tool_slug: get_weather
    parameters: {}
    description: Stateless weather tool
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.ToolConfig
  pk: 2
  fields:
    slug: calc-tool
    name: Calculator Tool
    tool_slug: calculate
    parameters: {}
    description: Stateless calculator tool
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.ToolConfig
  pk: 3
  fields:
    slug: search-docs-tool
    name: Search Documents Tool
    tool_slug: search_documents
    parameters:
      collections: [docs, manuals]
    description: Search tool configured for docs and manuals collections
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.AgentConfig
  pk: 1
  fields:
    slug: simple-bot
    name: Simple Bot
    description: A simple conversational agent
    implementation: simple_agent
    parameters:
      prompt: simple-prompt
      llm: local
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.AgentConfig
  pk: 2
  fields:
    slug: weather-bot
    name: Weather Bot
    description: Answers weather questions
    implementation: weather_agent
    parameters:
      prompt: weather-prompt
      llm: openai
      weather_tool: weather-tool
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.AgentConfig
  pk: 3
  fields:
    slug: rag-bot
    name: Documentation Bot
    description: Searches documentation for answers
    implementation: rag_agent
    parameters:
      prompt: rag-prompt
      llm: openai
      search_tool: search-docs-tool
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.AgentConfig
  pk: 4
  fields:
    slug: multi-tool-bot
    name: Multi-Tool Bot
    description: Agent with multiple tools
    implementation: multi_tool_agent
    parameters:
      prompt: simple-prompt
      llm: local
      weather_tool: weather-tool
      calc_tool: calc-tool
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z

- model: mops.AgentConfig
  pk: 5
  fields:
    slug: kitchen-sink-bot
    name: Kitchen Sink Bot
    description: Agent with all dependencies
    implementation: kitchen_sink_agent
    parameters:
      prompt: rag-prompt
      llm: openai
      collections: [docs, manuals]
      tools: [weather-tool, calc-tool, search-docs-tool]
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z
```

---

## Dependencies

### Task Dependencies Graph

```
Phase 1: Foundation
├── 1.1 Add new models (Prompt, ToolConfig, AgentConfig, slug/default_model to LLMProvider)
│   └── Create migration
└── 1.2 Create registry.py

Phase 2: Agent Code
├── 2.1 Create decorators.py
│   └── Requires: 1.2 (registry)
└── 2.2 Create resolver.py
    └── Requires: 1.1 (models), 1.2 (registry), 2.1 (decorators)

Phase 3: Migration
├── 3.1 Run migration from Phase 1.1
├── 3.2 Create data migration (Agent -> Prompt + AgentConfig)
│   └── Requires: 1.1 (models exist)
├── 3.3 Update Conversation model (agent -> agent_config)
│   └── Requires: 1.1 (AgentConfig exists)
│   └── Create migration
└── 3.4 Create legacy_agent wrapper
    └── Requires: 2.2 (resolver)

Phase 4: Integration
├── 4.1 Create tools.py (search_documents_tool_factory, etc.)
│   └── Requires: vector_store.py (existing)
├── 4.2 Create endpoints.py
│   └── Requires: 2.2 (resolver)
├── 4.3 Update urls.py + apps.py (AppConfig.ready())
│   └── Requires: 4.2 (endpoints)
└── 4.4 Add validation signals
    └── Requires: 2.2 (resolver)
    └── Register in apps.py

Phase 5: Quality
├── 5.1 Unit tests (registry, resolver, decorators, models)
│   └── Requires: All Phase 1, 2, 3, 4
├── 5.2 API tests
│   └── Requires: 4.2, 4.3
└── 5.3 Example app with fixtures
    └── Requires: All previous
```

### File Dependencies

```
mops/
├── models.py          # Phase 1.1 (Prompt, ToolConfig, AgentConfig, LLMProvider updates)
├── registry.py        # Phase 1.2
├── decorators.py      # Phase 2.1
├── resolver.py        # Phase 2.2
├── tools.py           # Phase 4.1
├── endpoints.py       # Phase 4.2
├── urls.py            # Phase 4.3
├── apps.py            # Phase 4.3, 4.4
├── signals.py         # Phase 4.4
└── vector_store.py    # Verify/exists

mops-example/
├── agents.py          # Phase 5.3
└── fixtures/
    └── agents.yaml    # Phase 5.3

migrations/
├── 00XX_add_prompt_toolconfig_agentconfig.py  # Phase 1.1
├── 00XX_add_slug_default_model_to_llmprovider.py # Phase 1.1
├── 00XX_update_conversation_agentconfig.py     # Phase 3.3
└── 00XX_migrate_agent_to_prompt_agentconfig.py # Phase 3.2

tests/
├── test_registry.py   # Phase 5.1
├── test_resolver.py   # Phase 5.1
├── test_decorators.py # Phase 5.1
├── test_models.py     # Phase 5.1
└── test_endpoints.py  # Phase 5.2
```

---

## Implementation Order (Recommended)

1. **Phase 1: Foundation** (can be done in parallel)
   - 1.1 Add models + migration
   - 1.2 Create registry.py

2. **Phase 2: Agent Code** (can be done in parallel after Phase 1)
   - 2.1 Create decorators.py
   - 2.2 Create resolver.py

3. **Phase 4: Integration - Tools & Endpoints** (can start after Phase 2)
   - 4.1 Create tools.py
   - 4.2 Create endpoints.py
   - 4.3 Update urls.py + apps.py
   - 4.4 Add validation signals

4. **Phase 3: Migration** (after Phase 1 models exist)
   - 3.1 Run migration from Phase 1.1
   - 3.2 Create data migration (Agent -> Prompt + AgentConfig)
   - 3.3 Update Conversation model + migration
   - 3.4 Create legacy_agent wrapper

5. **Phase 5: Quality** (after core functionality works)
   - 5.1 Write unit tests
   - 5.2 Write API tests
   - 5.3 Create example app with fixtures

---

## Checklist for Completion

- [ ] All user stories implemented
- [ ] All tests pass
- [ ] Example app demonstrates all features
- [ ] Documentation updated (README, docs)
- [ ] Migration path tested (destructive migration OK)
- [ ] Performance acceptable (no N+1 queries in resolver)
- [ ] Example project does not conflict with top-level uv config
