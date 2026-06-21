# Milestone 2 Implementation Plan - Code-Defined Agents

## Overview

This document outlines the step-by-step implementation plan for Milestone 2: Code-Defined Agents.
The milestone introduces a clean separation between agent code (implementations, tools) and configuration (prompts, providers, collections).

**Target State:** Developers write `@agent` decorated functions that receive dependencies (Prompt, LLMProvider, Collection, Tool) and return PydanticAI `Agent` objects. Configuration is stored in DB models and wired via `AgentConfig`.

---

## Phases

### Phase 1: Foundation (Models + Registry)
*Prerequisite for all other work. No breaking changes yet.*

### Phase 2: Agent Code (Decorators + Resolver)
*Enables writing agent functions. Still no breaking changes.*

### Phase 3: Migration (Data + Backward Compat)
*Migrates existing Agent model. Introduces breaking changes, requires data migration.*

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
      last_discovered = models.DateTimeField(null=True, blank=True)
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
_tool_registry: dict[str, PydanticTool] = {}


def register_agent(impl_name: str, factory: Callable):
    """Register an agent factory function by implementation name."""
    _agent_registry[impl_name] = factory


def register_tool(slug: str, tool_obj: PydanticTool):
    """Register a PydanticAI Tool by slug."""
    _tool_registry[slug] = tool_obj


def get_agent_factory(impl_name: str) -> Callable:
    """Get agent factory by implementation name."""
    if impl_name not in _agent_registry:
        raise KeyError(f"Agent implementation '{impl_name}' not registered")
    return _agent_registry[impl_name]


def get_tool(slug: str) -> PydanticTool:
    """Get tool by slug."""
    if slug not in _tool_registry:
        raise KeyError(f"Tool '{slug}' not registered")
    return _tool_registry[slug]


def list_agents() -> list[str]:
    """List all registered agent implementation names."""
    return list(_agent_registry.keys())


def list_tools() -> list[str]:
    """List all registered tool slugs."""
    return list(_tool_registry.keys())
```

---

### Phase 2: Agent Code

#### 2.1 Create Decorators
**File:** `mops/decorators.py` (new)

```python
from functools import wraps
from typing import Callable
from pydantic_ai import Tool as PydanticTool
from mops.registry import register_agent, register_tool


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
    Decorator that creates a PydanticAI Tool from a function and registers it.
    Returns the PydanticAI Tool object directly (not the original function).
    """
    def decorator(func: Callable):
        tool_obj = PydanticTool(func)
        registry_slug = slug or func.__name__
        register_tool(registry_slug, tool_obj)
        return tool_obj  # Returns PydanticAI Tool, not the function
    return decorator
```

#### 2.2 Create Resolver
**File:** `mops/resolver.py` (new)

```python
import inspect
from typing import get_origin, get_args, Any
from pydantic_ai import Tool as PydanticTool, Agent
from mops.models import Prompt, LLMProvider, Collection, AgentConfig
from mops.registry import get_agent_factory, get_tool

# Map of dependency types to their resolution strategies
_DB_TYPE_MAP = {
    Prompt: Prompt,
    LLMProvider: LLMProvider,
    Collection: Collection,
}


def resolve_dependency(param_type: type, slug: str | list[str]) -> Any:
    """
    Resolve a dependency slug (or list of slugs) to the actual object(s).

    Handles:
    - PydanticAI Tool types (from registry)
    - DB model types (Prompt, LLMProvider, Collection)
    - list[PydanticTool] (multiple tools from registry)
    - list[DB model] (multiple DB objects via slug__in query)
    """
    # Handle PydanticAI Tool types (resolved from registry, not DB)
    if param_type is PydanticTool:
        return get_tool(slug)

    # Handle list types: list[Tool], list[Collection], list[Prompt], list[LLMProvider]
    if get_origin(param_type) is list:
        inner_type = get_args(param_type)[0]

        # Handle list[PydanticTool]
        if inner_type is PydanticTool:
            return [get_tool(s) for s in slug]

        # Handle list of DB model types
        inner_model = _DB_TYPE_MAP.get(inner_type)
        if inner_model:
            return list(inner_model.objects.filter(slug__in=slug))

        raise ValueError(f"Unknown list dependency type: {param_type}")

    # Handle DB model types
    model_class = _DB_TYPE_MAP.get(param_type)
    if model_class:
        try:
            return model_class.objects.get(slug=slug)
        except model_class.DoesNotExist:
            raise ValueError(f"{model_class.__name__} with slug '{slug}' not found")

    raise ValueError(f"Unknown dependency type: {param_type}")


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
            raise ValueError(
                f"AgentConfig for '{config.slug}' missing parameter '{param_name}' "
                f"required by implementation '{config.implementation}'"
            )
        param_slug = config.parameters[param_name]
        param_type = param.annotation
        kwargs[param_name] = resolve_dependency(param_type, param_slug)

    return factory(**kwargs)


def validate_agent_config(config: AgentConfig) -> list[str]:
    """
    Validate that an AgentConfig's parameters match its implementation's signature.
    Returns list of error messages, empty if valid.
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

    # Check for missing parameters
    missing = param_names - config_param_names
    for p in missing:
        errors.append(f"Missing parameter '{p}' in config for implementation '{config.implementation}'")

    # Check for extra parameters
    extra = config_param_names - param_names
    for p in extra:
        errors.append(f"Extra parameter '{p}' in config not used by implementation '{config.implementation}'")

    return errors
```

---

### Phase 3: Migration

#### 3.1 Create new models in DB
- [ ] Run migration from Phase 1.1 to create Prompt, update LLMProvider, create AgentConfig

#### 3.2 Create data migration script
**File:** `mops/management/commands/migrate_to_code_defined.py`

```python
from django.core.management.base import BaseCommand
from mops.models import Agent, Prompt, LLMProvider, Collection, AgentConfig


class Command(BaseCommand):
    help = "Migrate existing Agent instances to Prompt + AgentConfig"

    def handle(self, *args, **options):
        # Migrate Agent -> Prompt
        for agent in Agent.objects.all():
            prompt, created = Prompt.objects.get_or_create(
                slug=agent.slug or f"prompt-{agent.id}",
                defaults={
                    "name": agent.name,
                    "text": agent.instructions or "",
                    "description": agent.description or "",
                }
            )
            self.stdout.write(f"Migrated Agent '{agent.name}' -> Prompt '{prompt.slug}'")

            # Create AgentConfig for each agent
            # Use a default implementation that wraps the old behavior
            config_slug = agent.slug or f"config-{agent.id}"

            # Build parameters based on old agent fields
            params = {
                "prompt": prompt.slug,
            }
            if agent.llm_provider:
                params["llm"] = agent.llm_provider.slug
            if agent.search_enabled and agent.allowed_collections.exists():
                params["collections"] = [c.slug for c in agent.allowed_collections.all()]

            AgentConfig.objects.get_or_create(
                slug=config_slug,
                defaults={
                    "name": agent.name,
                    "description": agent.description or "",
                    "implementation": "legacy_agent",  # Default wrapper
                    "parameters": params,
                }
            )
            self.stdout.write(f"  -> Created AgentConfig '{config_slug}'")

        self.stdout.write(self.style.SUCCESS("Migration complete"))
```

#### 3.3 Create legacy agent wrapper
**File:** `mops/agents.py` (new)

```python
"""Built-in agent implementations."""
from pydantic_ai import Agent
from mops import agent, tool
from mops.models import Prompt, LLMProvider, Collection


@agent
def legacy_agent(
    prompt: Prompt,
    llm: LLMProvider | None = None,
    collections: list[Collection] | None = None,
) -> Agent:
    """
    Legacy agent wrapper that mimics the old Agent model behavior.
    Used for backward compatibility during migration.
    """
    # Build model config
    model_config = {}
    if llm:
        model_config["model"] = llm.model_name if llm.model_name else None

    # Build tools
    tools = []
    if collections:
        from mops.tools import search_documents_tool
        tools.append(search_documents_tool)

    return Agent(
        instructions=prompt.text,
        tools=tools,
        **model_config
    )
```

#### 3.4 Update Conversation model
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
    null=True,
    blank=True
)
agent = models.ForeignKey(
    Agent,
    on_delete=models.CASCADE,
    related_name="legacy_conversations",
    null=True,
    blank=True
)
```

Create migration for this change.

#### 3.5 Backward compatibility layer
**File:** `mops/agents.py` (add to existing)

```python
# For backward compatibility, ensure old Agent-based endpoints still work
# This will be removed in a future version

def get_legacy_agent(agent: Agent) -> Agent:
    """Get a PydanticAI Agent from the old Agent model."""
    from pydantic_ai import Agent as PydanticAgent

    tools = []
    if agent.search_enabled and agent.allowed_collections.exists():
        from mops.tools import search_documents_tool
        tools.append(search_documents_tool)

    model_config = {}
    if agent.llm_provider and agent.model_name:
        model_config["model"] = agent.model_name

    return PydanticAgent(
        instructions=agent.instructions or "",
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
from pydantic_ai import Tool as PydanticTool
from mops import tool
from mops.models import Collection


@tool(slug="search_documents")
def search_documents_tool(query: str, collections: list[Collection]) -> str:
    """
    Search across configured document collections.

    Returns concatenated content of top matching chunks.
    """
    from mops.vector_store import search_similar

    results = []
    for collection in collections:
        chunks = search_similar(collection, query, k=3)
        results.extend([c.content for c in chunks])

    if not results:
        return "No matching documents found."

    return "\n\n".join(results)
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
        .extra(select={"similarity": "embedding <-> %s"})
    )[0:k]
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
        # TODO: Handle streaming? Or return full response?
        # For now, return synchronous response
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

# Dynamically add routes for each AgentConfig
# This needs to happen after app startup when AgentConfigs exist
# We'll use a lazy approach: register on first access or via signal

# For now, we can use a function to register all agents
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


# Call register_agent_routes on startup
# This can be done via AppConfig.ready() or a signal
# For now, we'll call it lazily on first /agents/ request
_agents_registered = False

@api.get("/agents/", include_in_schema=False)
def _list_agents_trigger(request):
    """Internal: triggers route registration on first access."""
    global _agents_registered
    if not _agents_registered:
        register_agent_routes()
        _agents_registered = True
    return list_agents(request)
```

Alternative: Use Django's `AppConfig.ready()`:

**File:** `mops/apps.py`
```python
from django.apps import AppConfig


class MopsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mops"

    def ready(self):
        # Import here to avoid circular imports
        from mops.urls import register_agent_routes
        register_agent_routes()
```

#### 4.4 Add validation signals
**File:** `mops/signals.py` (new)

```python
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from mops.models import AgentConfig
from mops.resolver import validate_agent_config


@receiver(pre_save, sender=AgentConfig)
def validate_agent_config_on_save(sender, instance, **kwargs):
    """Validate AgentConfig before saving."""
    if instance.pk:  # Only validate on update if implementation changed
        try:
            old = AgentConfig.objects.get(pk=instance.pk)
            if old.implementation != instance.implementation:
                errors = validate_agent_config(instance)
                if errors:
                    raise ValueError("; ".join(errors))
        except AgentConfig.DoesNotExist:
            pass
    else:  # New instance
        errors = validate_agent_config(instance)
        if errors:
            raise ValueError("; ".join(errors))
```

Register signals in `mops/apps.py`:
```python
class MopsConfig(AppConfig):
    # ...
    def ready(self):
        from mops.urls import register_agent_routes
        register_agent_routes()

        # Import signals to register them
        from mops import signals  # noqa: F401
```

---

### Phase 5: Quality

#### 5.1 Unit Tests
**File:** `tests/test_registry.py`

```python
import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import (
    register_agent, register_tool, get_agent_factory, get_tool,
    list_agents, list_tools
)


def test_agent_registration():
    def my_agent(prompt):
        return Agent(instructions=prompt)

    register_agent("my_agent", my_agent)
    assert "my_agent" in list_agents()
    assert get_agent_factory("my_agent") is my_agent


def test_tool_registration():
    def my_tool(x: int) -> int:
        return x * 2

    tool_obj = PydanticTool(my_tool)
    register_tool("my_tool", tool_obj)
    assert "my_tool" in list_tools()
    assert get_tool("my_tool") is tool_obj


def test_get_nonexistent_agent():
    with pytest.raises(KeyError):
        get_agent_factory("nonexistent")


def test_get_nonexistent_tool():
    with pytest.raises(KeyError):
        get_tool("nonexistent")
```

**File:** `tests/test_resolver.py`

```python
import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.models import Prompt, LLMProvider, Collection, AgentConfig
from mops.resolver import resolve_dependency, get_agent, validate_agent_config
from mops.registry import register_agent, register_tool


@pytest.mark.django_db
class TestResolveDependency:
    def test_resolve_prompt(self):
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")
        result = resolve_dependency(Prompt, "test-prompt")
        assert result.slug == "test-prompt"

    def test_resolve_llm_provider(self):
        provider = LLMProvider.objects.create(
            slug="test-provider", name="Test", url="http://test.com"
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

    def test_resolve_tool(self):
        def my_tool(x: int) -> int:
            return x * 2
        tool_obj = PydanticTool(my_tool)
        register_tool("my_tool", tool_obj)
        result = resolve_dependency(PydanticTool, "my_tool")
        assert result is tool_obj

    def test_resolve_list_of_tools(self):
        def tool1(x: int) -> int:
            return x * 2
        def tool2(x: int) -> int:
            return x + 1

        tool1_obj = PydanticTool(tool1)
        tool2_obj = PydanticTool(tool2)
        register_tool("tool1", tool1_obj)
        register_tool("tool2", tool2_obj)

        result = resolve_dependency(list[PydanticTool], ["tool1", "tool2"])
        assert len(result) == 2

    def test_resolve_nonexistent(self):
        with pytest.raises(ValueError, match="not found"):
            resolve_dependency(Prompt, "nonexistent")


@pytest.mark.django_db
class TestGetAgent:
    def test_get_agent_success(self):
        # Create config
        prompt = Prompt.objects.create(slug="test-prompt", name="Test", text="Hello")

        @agent
        def test_agent(prompt: Prompt) -> Agent:
            return Agent(instructions=prompt.text)

        config = AgentConfig.objects.create(
            slug="test-agent",
            name="Test Agent",
            implementation="test_agent",
            parameters={"prompt": "test-prompt"}
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

    def test_missing_parameter(self):
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
        assert "Missing parameter 'llm'" in errors[0]

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
```

**File:** `tests/test_decorators.py`

```python
import pytest
from pydantic_ai import Agent, Tool as PydanticTool
from mops.registry import list_agents, list_tools, get_agent_factory, get_tool
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
    def test_tool_decorator_registers_tool(self):
        @tool
        def my_tool(x: int) -> int:
            return x * 2

        assert "my_tool" in list_tools()
        registered_tool = get_tool("my_tool")
        assert isinstance(registered_tool, PydanticTool)

    def test_tool_decorator_returns_tool_object(self):
        @tool
        def my_tool(x: int) -> int:
            return x * 2

        assert isinstance(my_tool, PydanticTool)

    def test_tool_decorator_with_custom_slug(self):
        @tool(slug="custom_slug")
        def my_tool(x: int) -> int:
            return x * 2

        assert "custom_slug" in list_tools()
        assert get_tool("custom_slug") is my_tool
```

**File:** `tests/test_models.py`

```python
import pytest
from mops.models import Prompt, LLMProvider, Collection, AgentConfig


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
    def test_create_provider_with_slug(self):
        provider = LLMProvider.objects.create(
            slug="openai",
            name="OpenAI",
            url="https://api.openai.com/v1",
            available_models=["gpt-4", "gpt-3.5-turbo"]
        )
        assert provider.slug == "openai"


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
from mops.models import Prompt, AgentConfig
from mops.registry import register_agent
from pydantic_ai import Agent


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
        @register_agent("test_agent_impl", lambda prompt: Agent(instructions="test"))
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
```

#### 5.2 API Tests

Use the existing test infrastructure to test:
- Agent registration via decorator works
- REST endpoints are created automatically
- Agent execution returns correct responses
- Error handling for invalid configs
- Streaming support (if implemented)

#### 5.3 Example App
**File:** `mops-example/agents.py` (new)

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

@tool
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    # In a real app, this would call a weather API
    return f"The weather in {city} is sunny and 72°F."


@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers."""
    return a + b


# =============================================================================
# Agents
# =============================================================================

@agent
def simple_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
    """
    A simple agent that just uses a prompt and LLM provider.
    """
    return Agent(
        instructions=prompt.text,
        model=llm.model_name if llm.model_name else None,
    )


@agent
def weather_agent(
    prompt: Prompt,
    llm: LLMProvider,
    tools: list[PydanticTool],
) -> Agent:
    """
    An agent that can answer weather questions using the get_weather tool.
    """
    return Agent(
        instructions=prompt.text,
        model=llm.model_name if llm.model_name else None,
        tools=tools,
    )


@agent
def rag_agent(
    prompt: Prompt,
    llm: LLMProvider,
    collections: list[Collection],
) -> Agent:
    """
    A RAG agent that can search documents in configured collections.
    """
    from mops.tools import search_documents_tool

    return Agent(
        instructions=prompt.text,
        model=llm.model_name if llm.model_name else None,
        tools=[search_documents_tool],
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
    return Agent(
        instructions=prompt.text,
        model=llm.model_name if llm.model_name else None,
        tools=[weather_tool, calc_tool],
    )
```

**File:** `mops-example/fixtures/agents.yaml` (new)

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
    last_discovered: null

- model: mops.LLMProvider
  pk: 2
  fields:
    slug: openai
    name: OpenAI
    url: https://api.openai.com/v1
    available_models: ["gpt-4", "gpt-3.5-turbo"]
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
      tools: [get_weather]
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
      collections: [docs, manuals]
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
      weather_tool: get_weather
      calc_tool: calculate_sum
    created_at: 2024-01-01T00:00:00Z
    updated_at: 2024-01-01T00:00:00Z
```

---

## Dependencies

### Task Dependencies Graph

```
Phase 1: Foundation
├── 1.1 Add new models (Prompt, AgentConfig, slug to LLMProvider)
│   └── Create migration
└── 1.2 Create registry.py

Phase 2: Agent Code
├── 2.1 Create decorators.py
│   └── Requires: 1.2 (registry)
└── 2.2 Create resolver.py
    └── Requires: 1.1 (models), 1.2 (registry), 2.1 (decorators)

Phase 3: Migration
├── 3.1 Create migration script
│   └── Requires: 1.1 (migration run)
├── 3.2 Create legacy_agent wrapper
│   └── Requires: 2.2 (resolver), 4.1 (tools)
├── 3.3 Update Conversation model
│   └── Requires: 1.1 (AgentConfig exists)
│   └── Create migration
├── 3.4 Backward compatibility layer
│   └── Requires: 3.2 (legacy_agent)
└── 3.5 Run migrations
    └── Requires: 1.1, 3.3 migrations

Phase 4: Integration
├── 4.1 Create tools.py (search_documents_tool)
│   └── Requires: vector_store.py (existing)
├── 4.2 Create endpoints.py
│   └── Requires: 2.2 (resolver)
├── 4.3 Update urls.py
│   └── Requires: 4.2 (endpoints)
├── 4.4 Add validation signals
│   └── Requires: 2.2 (resolver)
│   └── Register in apps.py
└── 4.5 Register agents in example app
    └── Requires: All Phase 2, 4.1

Phase 5: Quality
├── 5.1 Unit tests (registry, resolver, decorators, models)
│   └── Requires: All Phase 1, 2, 3, 4
├── 5.2 API tests
│   └── Requires: 4.2, 4.3
└── 5.3 Example app
    └── Requires: All previous
```

### File Dependencies

```
mops/
├── models.py          # Phase 1.1
├── registry.py        # Phase 1.2
├── decorators.py      # Phase 2.1
├── resolver.py        # Phase 2.2
├── tools.py           # Phase 4.1
├── endpoints.py       # Phase 4.2
├── urls.py            # Phase 4.3
├── apps.py            # Updated Phase 4.3, 4.4
├── signals.py         # Phase 4.4
└── vector_store.py    # Verify/exists

mops-example/
├── agents.py          # Phase 5.3
└── fixtures/
    └── agents.yaml    # Phase 5.3

tests/
├── test_registry.py   # Phase 5.1
├── test_resolver.py   # Phase 5.1
├── test_decorators.py # Phase 5.1
├── test_models.py     # Phase 5.1
└── test_endpoints.py  # Phase 5.2

migrations/
├── 00XX_add_prompt_agentconfig.py  # Phase 1.1
├── 00XX_add_slug_to_llmprovider.py # Phase 1.1
└── 00XX_update_conversation.py     # Phase 3.3
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
   - 4.3 Update urls.py
   - 4.4 Add validation signals

4. **Phase 3: Migration** (after Phase 1 models exist)
   - 3.1 Create migration script
   - 3.2 Create legacy_agent wrapper
   - 3.3 Update Conversation model + migration
   - 3.4 Backward compatibility layer
   - 3.5 Run migrations

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
- [ ] Backward compatibility verified
- [ ] Migration path tested
- [ ] Performance acceptable (no N+1 queries in resolver)
