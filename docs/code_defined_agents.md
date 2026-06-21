# Code-Defined Agents

## Overview

Separate code (agent implementations, tools) from configuration (prompts, providers, collections, tool configs).

- **Code**: Agent functions registered via `@agent`, tool **factories** registered via `@tool`.
- **Configuration**: `Prompt`, `LLMProvider`, `Collection`, `ToolConfig` models stored in DB.
- **Wiring**: `AgentConfig` maps URL slugs to implementations + dependency slugs.

**Key Change:** Tools are now registered as **factories** (not pre-configured `PydanticTool` objects). Parameterized tools (e.g., `search_documents` with `collections`) are configured via `ToolConfig` instances, which store the factory slug and runtime parameters.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CODE (agents.py)                                               │
│                                                             │
│  @agent                                                      │
│  def rag_agent(                                               │
│      prompt: Prompt,                                          │
│      llm: LLMProvider,                                       │
│      search_tool: PydanticTool,  # ← Injected from ToolConfig │
│  ) -> Agent:                                                 │
│      return Agent(                                           │
│          instructions=prompt.text,                           │
│          model=llm.default_model,                          │
│          tools=[search_tool],  # Already a PydanticTool     │
│      )                                                       │
│                                                             │
│  @tool(slug="search_documents")                             │
│  def search_documents_tool_factory(                          │
│      collections: list[Collection], **kwargs                │
│  ) -> PydanticTool:                                         │
│      # Factory returns a PydanticTool configured with      │
│      # the provided collections                              │
│      def search(query: str) -> str:                         │
│          ...                                                 │
│      return PydanticTool(search)                             │
│                                                             │
│  @tool(slug="get_weather")                                  │
│  def get_weather_tool_factory(**kwargs) -> PydanticTool:    │
│      # Stateless factory (no runtime params)               │
│      def get_weather(city: str) -> str:                     │
│          return f"Sunny in {city}"                          │
│      return PydanticTool(get_weather)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  REGISTRY (mops/registry.py)                                  │
│  - agents: {"rag_agent": <factory>}                        │
│  - tool_factories: {"search_documents": <factory>, ...}    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  CONFIGURATION (DB Models)                                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │  Prompt      │  │ LLMProvider   │                          │
│  │  - slug      │  │  - slug       │                          │
│  │  - text      │  │  - name       │                          │
│  │  - name      │  │  - url        │                          │
│  │  - desc      │  │  - default_model│ ← NEW                   │
│  └──────────────┘  └──────────────┘                          │
│                                                             │
│  ┌──────────────────────┐                                      │
│  │   Collection         │                                      │
│  │  - slug              │  ←─ RAG document sets                │
│  │  - name              │                                      │
│  │  - description       │                                      │
│  └──────────────────────┘                                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  ToolConfig                                            ││
│  │  - slug: "search-docs"                                ││
│  │  - tool_slug: "search_documents"  # factory name        ││
│  │  - parameters: {"collections": ["docs", "manuals"]}    ││
│  │  - description: "Search tool for docs and manuals"      ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  AgentConfig                                            ││
│  │  - slug: "rag-bot"                                     ││
│  │  - implementation: "rag_agent"                         ││
│  │  - parameters: {                                        ││
│  │      "prompt": "rag-prompt",                           ││
│  │      "llm": "openai",                                 ││
│  │      "search_tool": "search-docs"  # ToolConfig slug    ││
│  │    }                                                    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  RUNTIME FLOW                                                 │
│  get_agent("rag-bot"):                                      │
│  1. Load AgentConfig by slug                                  │
│  2. Get factory from registry[config.implementation]        │
│  3. Inspect factory signature                                │
│  4. For each param: resolve slugs → objects                  │
│     - DB models: fetch from DB (Prompt, LLMProvider, etc.)  │
│     - PydanticTool: fetch ToolConfig → call factory          │
│       with ToolConfig.parameters → return PydanticTool       │
│     - list[PydanticTool]: fetch multiple ToolConfigs        │
│  5. Call factory(**resolved_params) → Agent                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Models

### Prompt
```python
class Prompt(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    text = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### LLMProvider
```python
class LLMProvider(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField()
    available_models = models.JSONField(default=list)
    default_model = models.CharField(max_length=255, blank=True)  # Default model for this provider
    last_discovered = models.DateTimeField(null=True, blank=True)
```

### Collection
```python
class Collection(models.Model):
    """A set of documents to be indexed and searched (RAG)."""
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
```

### ToolConfig
**NEW:** Stores configuration for parameterized tools.
```python
class ToolConfig(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    tool_slug = models.CharField(max_length=255)  # Registered tool factory name (e.g., "search_documents")
    parameters = models.JSONField(default=dict)  # Runtime parameters for the tool factory (e.g., {"collections": ["docs"]})
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### AgentConfig
```python
class AgentConfig(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    implementation = models.CharField(max_length=255)  # registered function name
    parameters = models.JSONField(default=dict)  # {"param_name": "slug" | ["slug1", ...], ...}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## Registry

### mops/registry.py
```python
from typing import Callable
from pydantic_ai import Agent, Tool as PydanticTool

_agent_registry: dict[str, Callable] = {}
_tool_factory_registry: dict[str, Callable] = {}  # Stores factories, not PydanticTool objects


def register_agent(impl_name: str, factory: Callable):
    _agent_registry[impl_name] = factory


def register_tool_factory(tool_slug: str, factory: Callable):
    """Register a tool factory by slug. The factory must accept **kwargs and return a PydanticTool."""
    _tool_factory_registry[tool_slug] = factory


def get_agent_factory(impl_name: str) -> Callable:
    return _agent_registry[impl_name]


def get_tool_factory(tool_slug: str) -> Callable:
    return _tool_factory_registry[tool_slug]
```

### Decorators
```python
# mops/decorators.py
from pydantic_ai import Tool as PydanticTool
from mops.registry import register_agent, register_tool_factory


def agent(func: Callable) -> Callable:
    """Register an agent factory by its function name."""
    register_agent(func.__name__, func)
    return func


def tool(*, slug: str = None):
    """
    Register a tool factory function.
    The factory must accept **kwargs and return a PydanticAI Tool.
    Returns the original function (not a PydanticTool).
    """
    def decorator(func: Callable):
        registry_slug = slug or func.__name__
        register_tool_factory(registry_slug, func)
        return func  # Returns the original factory function
    return decorator
```

---

## Resolution

### mops/resolver.py
```python
import inspect
from typing import get_origin, get_args, Union
from pydantic_ai import Tool as PydanticTool
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.registry import get_agent_factory, get_tool_factory

# Custom exceptions
class DependencyNotFoundError(ValueError):
    """Raised when a dependency slug is not found."""
    pass

class InvalidTypeError(ValueError):
    """Raised when a dependency type is invalid or unsupported."""
    pass


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
    - list[PydanticTool] (multiple ToolConfigs → multiple PydanticTools)
    - list[DB model] (multiple DB objects via slug__in query)
    - Optional types (e.g., Prompt | None)
    - None values (for Optional parameters)
    """
    # Handle None (for Optional parameters)
    if slug is None:
        if get_origin(param_type) is Union and type(None) in get_args(param_type):
            return None
        raise InvalidTypeError(f"Non-optional parameter {param_type} cannot be None")

    # Handle PydanticAI Tool types (resolved from ToolConfig + factory)
    if param_type is PydanticTool:
        tool_config = ToolConfig.objects.get(slug=slug)
        factory = get_tool_factory(tool_config.tool_slug)
        return factory(**tool_config.parameters)

    # Handle list types
    if get_origin(param_type) is list:
        inner_type = get_args(param_type)[0]

        # Handle list[PydanticTool]
        if inner_type is PydanticTool:
            tool_configs = ToolConfig.objects.filter(slug__in=slug)
            return [get_tool_factory(tc.tool_slug)(**tc.parameters) for tc in tool_configs]

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
    Resolve an agent by slug, injecting all dependencies.
    
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
            if param.default is inspect.Parameter.empty:
                raise DependencyNotFoundError(
                    f"AgentConfig for '{config.slug}' missing parameter '{param_name}' "
                    f"required by implementation '{config.implementation}'"
                )
            kwargs[param_name] = param.default
            continue

        param_slug = config.parameters[param_name]
        param_type = param.annotation
        kwargs[param_name] = resolve_dependency(param_type, param_slug)

    return factory(**kwargs)
```

---

## Built-in Tools

### Document Search Tool
For RAG-enabled agents, provide a built-in tool factory that creates a `PydanticTool` configured with specific collections:

```python
# mops/tools.py
from pydantic_ai import Tool as PydanticTool
from mops import tool
from mops.models import Collection


@tool(slug="search_documents")
def search_documents_tool_factory(collections: list[Collection], **kwargs) -> PydanticTool:
    """
    Factory for a document search tool.
    Creates a PydanticAI Tool configured to search the provided collections.
    
    Args:
        collections: List of Collection objects to search in.
        **kwargs: Additional parameters (unused, for forward compatibility).
    
    Returns:
        A PydanticAI Tool that searches the configured collections.
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
```

### Stateless Tools
Tools that don't require runtime configuration can be registered as simple factories:

```python
@tool(slug="get_weather")
def get_weather_tool_factory(**kwargs) -> PydanticTool:
    """Factory for a stateless weather tool."""
    def get_weather(city: str) -> str:
        """Get weather information for a city."""
        return f"The weather in {city} is sunny and 72°F."
    return PydanticTool(get_weather)
```

---

## Endpoints

### mops/endpoints.py
```python
from ninja import Router
from mops.resolver import get_agent


def create_agent_router(slug: str) -> Router:
    router = Router()

    @router.post("/")
    def run_agent(request, message: str):
        agent = get_agent(slug)
        result = agent.run(message)
        return {"response": str(result)}

    @router.get("/")
    def get_info(request):
        config = AgentConfig.objects.get(slug=slug)
        return {
            "slug": config.slug,
            "name": config.name,
            "description": config.description,
            "implementation": config.implementation,
        }

    return router
```

### mops/urls.py
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
    return [
        {"slug": c.slug, "name": c.name, "description": c.description}
        for c in AgentConfig.objects.all()
    ]
```

### mops/apps.py
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

---

## Example Usage

### Define agents and tools
```python
# myproject/agents.py
from pydantic_ai import Agent, Tool as PydanticTool
from mops import agent, tool
from mops.models import Prompt, LLMProvider, Collection


# Stateless tool (no runtime config)
@tool(slug="get_weather")
def get_weather_tool_factory(**kwargs) -> PydanticTool:
    def get_weather(city: str) -> str:
        return f"Sunny in {city}"
    return PydanticTool(get_weather)


# Parameterized tool (requires collections)
@tool(slug="search_documents")
def search_documents_tool_factory(collections: list[Collection], **kwargs) -> PydanticTool:
    def search(query: str) -> str:
        from mops.vector_store import search_similar
        results = []
        for collection in collections:
            chunks = search_similar(collection, query, k=3)
            results.extend([c.content for c in chunks])
        return "\n\n".join(results) if results else "No results"
    return PydanticTool(search)


# Simple agent (no tools)
@agent
def simple_agent(prompt: Prompt, llm: LLMProvider) -> Agent:
    return Agent(
        instructions=prompt.text,
        model=llm.default_model if llm.default_model else None,
    )


# Agent with a parameterized tool
@agent
def rag_agent(
    prompt: Prompt,
    llm: LLMProvider,
    search_tool: PydanticTool,  # Injected from ToolConfig
) -> Agent:
    return Agent(
        instructions=prompt.text,
        model=llm.default_model if llm.default_model else None,
        tools=[search_tool],
    )


# Agent with multiple tools
@agent
def multi_tool_agent(
    prompt: Prompt,
    llm: LLMProvider,
    weather_tool: PydanticTool,
    search_tool: PydanticTool,
) -> Agent:
    return Agent(
        instructions=prompt.text,
        model=llm.default_model if llm.default_model else None,
        tools=[weather_tool, search_tool],
    )


# Agent with direct collection dependencies
@agent
def rag_agent_inline(
    prompt: Prompt,
    llm: LLMProvider,
    collections: list[Collection],
) -> Agent:
    # Create the search tool inline with the collections
    from mops.tools import search_documents_tool_factory
    search_tool = search_documents_tool_factory(collections=collections)
    return Agent(
        instructions=prompt.text,
        model=llm.default_model if llm.default_model else None,
        tools=[search_tool],
    )
```

### Configure in DB (via admin or fixtures)
```python
# ToolConfigs (parameterized tools)
ToolConfig.objects.create(
    slug="search-docs",
    name="Search Docs Tool",
    tool_slug="search_documents",  # References the registered factory
    parameters={"collections": ["docs", "manuals"]},  # Runtime parameters for the factory
)

ToolConfig.objects.create(
    slug="weather-tool",
    name="Weather Tool",
    tool_slug="get_weather",
    parameters={},  # No runtime parameters needed
)

# Prompt
Prompt.objects.create(slug="rag-prompt", text="You are a documentation assistant.")

# LLMProvider
LLMProvider.objects.create(
    slug="openai",
    name="OpenAI",
    url="https://api.openai.com/v1",
    default_model="gpt-4"
)

# Collections
Collection.objects.create(slug="docs", name="Documentation")
Collection.objects.create(slug="manuals", name="Manuals")

# AgentConfigs
AgentConfig.objects.create(
    slug="rag-bot",
    name="Documentation Bot",
    implementation="rag_agent",
    parameters={
        "prompt": "rag-prompt",
        "llm": "openai",
        "search_tool": "search-docs",  # ToolConfig slug
    },
)

AgentConfig.objects.create(
    slug="multi-tool-bot",
    name="Multi-Tool Bot",
    implementation="multi_tool_agent",
    parameters={
        "prompt": "rag-prompt",
        "llm": "openai",
        "weather_tool": "weather-tool",  # ToolConfig slug
        "search_tool": "search-docs",    # ToolConfig slug
    },
)

AgentConfig.objects.create(
    slug="inline-rag-bot",
    name="Inline RAG Bot",
    implementation="rag_agent_inline",
    parameters={
        "prompt": "rag-prompt",
        "llm": "openai",
        "collections": ["docs", "manuals"],  # Direct collection slugs
    },
)
```

### Use agents
```python
from mops.resolver import get_agent

# Agent with ToolConfig-injected tools
agent = get_agent("rag-bot")
response = agent.run("How do I use the API?")

# Agent with multiple tools
agent = get_agent("multi-tool-bot")
response = agent.run("What's the weather in Berlin and how do I use the API?")

# Agent with inline collection resolution
agent = get_agent("inline-rag-bot")
response = agent.run("Tell me about the product")
```

---

## Document Ingestion Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Upload Document to Collection                             │
│     POST /collections/{slug}/documents/                       │
│     → Document.model created                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Process Document (async task)                             │
│     - Split into chunks                                       │
│     - Generate embeddings                                     │
│     - Store in DocumentChunk with vector field                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Create ToolConfig for search_documents                    │
│     ToolConfig.objects.create(                                │
│         slug="search-docs",                                   │
│         tool_slug="search_documents",                        │
│         parameters={"collections": ["docs"]}                 │
│     )                                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. AgentConfig references ToolConfig                         │
│     parameters: {"search_tool": "search-docs"}               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. At runtime: resolver instantiates PydanticTool            │
│     - Load ToolConfig by slug                                 │
│     - Get tool factory from registry                          │
│     - Call factory(**ToolConfig.parameters) → PydanticTool   │
│     - Inject into agent                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Benefits

1. **No wrapping**: Tools are registered as factories and instantiated as `PydanticTool` objects directly.
2. **Flexible**: Tools can accept runtime parameters (e.g., `collections`) via `ToolConfig`.
3. **Dynamic**: Tool slugs in `AgentConfig` reference `ToolConfig` instances, which can be reconfigured without code changes.
4. **Clean separation**: Code (tools, agents) vs Configuration (DB models) vs Wiring (`AgentConfig`, `ToolConfig`).
5. **Type-safe**: Dependencies are resolved based on type annotations (e.g., `PydanticTool` vs `Collection`).

---

## Dependencies

- Django >= 6.0
- pydantic-ai >= 0.0.12
- ninja-api >= 1.0
- pgvector (for vector search in PostgreSQL)

---

## Success Criteria

1. `@tool` decorator registers **factories** that return `PydanticTool` objects.
2. `ToolConfig` stores runtime parameters for tool factories.
3. Agent functions receive `PydanticTool` objects directly (no wrapping needed).
4. `AgentConfig.parameters` references `ToolConfig` slugs for tools.
5. Resolution handles both DB models and `ToolConfig` → `PydanticTool` instantiation.
6. Collections integrate seamlessly as a dependency type.
7. Changing DB config (collections, prompt, provider, tools) affects runtime behavior.
8. All agents automatically get REST endpoints.
9. Custom exceptions (`DependencyNotFoundError`, `InvalidTypeError`) are used for error handling.
