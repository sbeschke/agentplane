# Code-Defined Agents

## Overview

Separate code (agent implementations, tools) from configuration (prompts, providers, collections).

- **Code**: Agent functions registered via `@agent`, tools return PydanticAI `Tool` objects via `@tool`
- **Configuration**: Prompt, LLMProvider, Collection models stored in DB
- **Wiring**: AgentConfig maps URL slugs to implementations + dependency slugs

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
│      collections: list[Collection],                          │
│      tools: list[Tool],  # ← PydanticAI Tool objects         │
│  ) -> Agent:                                                 │
│      return Agent(                                           │
│          instructions=prompt.text,                           │
│          model=llm.model_name,                               │
│          tools=tools,  # Directly usable                     │
│      )                                                       │
│                                                             │
│  @tool                                                       │
│  def get_weather(city: str) -> str:                           │
│      return f"Sunny in {city}"                               │
│  # get_weather is now a PydanticAI Tool                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  REGISTRY (mops/registry.py)                                  │
│  - agents: {"rag_agent": <factory>}                        │
│  - tools: {"get_weather": <PydanticAI Tool>}                │
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
│  │  AgentConfig                                            ││
│  │  - slug: "rag-bot"                                     ││
│  │  - implementation: "rag_agent"                         ││
│  │  - parameters: {                                        ││
│  │      "prompt": "rag-prompt",                           ││
│  │      "llm": "openai",                                 ││
│  │      "collections": ["docs", "manuals"],              ││
│  │      "tools": ["get_weather"]  # → Tool registry slugs   ││
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
│     - DB models: fetch from DB                              │
│     - Tool types: fetch from tool registry                   │
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
_tool_registry: dict[str, PydanticTool] = {}

def register_agent(impl_name: str, factory: Callable):
    _agent_registry[impl_name] = factory

def register_tool(slug: str, tool_obj: PydanticTool):
    _tool_registry[slug] = tool_obj

def get_agent_factory(impl_name: str) -> Callable:
    return _agent_registry[impl_name]

def get_tool(slug: str) -> PydanticTool:
    return _tool_registry[slug]
```

### Decorators
```python
# mops/decorators.py
from pydantic_ai import Tool as PydanticTool
from mops.registry import register_agent, register_tool

def agent(func: Callable) -> Callable:
    """Register an agent factory by its function name."""
    register_agent(func.__name__, func)
    return func

def tool(*, slug: str = None):
    """Create a PydanticAI Tool and register it. Returns the Tool."""
    def decorator(func: Callable):
        tool_obj = PydanticTool(func)
        registry_slug = slug or func.__name__
        register_tool(registry_slug, tool_obj)
        return tool_obj  # Returns PydanticAI Tool directly
    return decorator
```

---

## Resolution

### mops/resolver.py
```python
import inspect
from typing import get_origin, get_args
from pydantic_ai import Tool as PydanticTool
from mops.models import Prompt, LLMProvider, Collection, AgentConfig
from mops.registry import get_agent_factory, get_tool

_DB_TYPE_MAP = {
    Prompt: Prompt,
    LLMProvider: LLMProvider,
    Collection: Collection,
}

def resolve_dependency(param_type, slug: str | list[str]):
    """Resolve a dependency slug (or list of slugs) to object(s)."""
    # Handle PydanticAI Tool types (resolved from registry, not DB)
    if param_type is PydanticTool:
        return get_tool(slug)

    if get_origin(param_type) is list:
        inner_type = get_args(param_type)[0]

        # Handle list[PydanticTool]
        if inner_type is PydanticTool:
            return [get_tool(s) for s in slug]

        # Handle list of DB model types (list[Collection], list[Prompt], etc.)
        inner_model = _DB_TYPE_MAP.get(inner_type)
        if inner_model:
            return list(inner_model.objects.filter(slug__in=slug))

    # Handle DB model types
    model_class = _DB_TYPE_MAP.get(param_type)
    if model_class:
        return model_class.objects.get(slug=slug)

    raise ValueError(f"Unknown dependency type: {param_type}")

def get_agent(slug: str) -> Agent:
    """Resolve an agent by slug, injecting all dependencies."""
    config = AgentConfig.objects.get(slug=slug)
    factory = get_agent_factory(config.implementation)
    sig = inspect.signature(factory)

    kwargs = {}
    for param_name, param in sig.parameters.items():
        param_slug = config.parameters[param_name]
        param_type = param.annotation
        kwargs[param_name] = resolve_dependency(param_type, param_slug)

    return factory(**kwargs)
```

---

## Built-in Tools

### Document Search Tool
For RAG-enabled agents, provide a built-in tool that searches configured collections:

```python
# mops/tools.py
from pydantic_ai import Tool as PydanticTool
from mops.models import Collection

@tool(slug="search_documents")
def search_documents_tool(query: str, collections: list[Collection]) -> str:
    """Search across configured document collections."""
    from mops.vector_store import search_similar

    results = []
    for collection in collections:
        chunks = search_similar(collection, query, k=3)
        results.extend([c.content for c in chunks])

    return "\n\n".join(results)

# search_documents_tool is a PydanticAI Tool, registered as "search_documents"
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
        return {"response": result}

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

---

## Example Usage

### Define agents and tools
```python
# myproject/agents.py
from pydantic_ai import Agent, Tool as PydanticTool
from mops import agent, tool
from mops.models import Prompt, LLMProvider, Collection

# Tools return PydanticAI Tool objects directly
@tool  # Registered as "get_weather", returns PydanticAI Tool
def get_weather(city: str) -> str:
    return f"Sunny in {city}"

@agent
def weather_agent(
    prompt: Prompt,
    llm: LLMProvider,
    tools: list[PydanticTool],  # Already PydanticAI Tools
) -> Agent:
    return Agent(
        instructions=prompt.text,
        model=llm.model_name,
        tools=tools,  # No wrapping needed!
    )

@agent
def rag_agent(
    prompt: Prompt,
    llm: LLMProvider,
    collections: list[Collection],
) -> Agent:
    from mops.tools import search_documents_tool
    return Agent(
        instructions=prompt.text,
        model=llm.model_name,
        tools=[search_documents_tool],  # Already a PydanticAI Tool
    )

# Or inline the search tool with collections injected
@agent
def rag_agent_inline(
    prompt: Prompt,
    llm: LLMProvider,
    collections: list[Collection],
    search_tool: PydanticTool,  # Injected from config
) -> Agent:
    return Agent(
        instructions=prompt.text,
        model=llm.model_name,
        tools=[search_tool],
    )
```

### Configure in DB (via admin or fixtures)
```python
# AgentConfig referencing tools by registry slug
AgentConfig.objects.create(
    slug="weather-bot",
    name="Weather Assistant",
    implementation="weather_agent",
    parameters={
        "prompt": "weather-prompt",
        "llm": "openai",
        "tools": ["get_weather"],  # Tool registry slugs
    },
)

AgentConfig.objects.create(
    slug="rag-bot",
    name="Document Search Assistant",
    implementation="rag_agent_inline",
    parameters={
        "prompt": "rag-prompt",
        "llm": "openai",
        "collections": ["product-docs", "api-docs"],
        "search_tool": "search_documents",  # Built-in tool slug
    },
)

# Prompt
Prompt.objects.create(slug="weather-prompt", text="You are a weather assistant.")
Prompt.objects.create(slug="rag-prompt",
    text="You are a helpful assistant with access to documentation.")

# LLMProvider
LLMProvider.objects.create(slug="openai", name="OpenAI", url="https://api.openai.com/v1")

# Collections
Collection.objects.create(slug="product-docs", name="Product Documentation")
Collection.objects.create(slug="api-docs", name="API Documentation")
```

### Use agents
```python
from mops.resolver import get_agent

# Tools are already PydanticAI Tools, no wrapping needed
agent = get_agent("weather-bot")
response = agent.run("What's the weather in Berlin?")

# RAG agent uses injected collections
agent = get_agent("rag-bot")
response = agent.run("How do I use the API?")
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
│  3. AgentConfig references Collection                         │
│     parameters: {"collections": ["product-docs", "api-docs"]}   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. At runtime: search_documents_tool uses Collection         │
│     - Filters DocumentChunk by collection                     │
│     - Vector search via pgvector                              │
│     - Returns top matches to agent                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Benefits

1. **No wrapping**: `@tool` returns PydanticAI `Tool` directly, agents use them as-is
2. **Flexible**: Tools can accept any parameters (including `list[Collection]`)
3. **Dynamic**: Tool slugs in AgentConfig can reference any registered tool
4. **Clean separation**: Code (tools, agents) vs Configuration (DB models) vs Wiring (AgentConfig)

---

## Dependencies

- Django >= 6.0
- pydantic-ai >= 0.0.12
- ninja-api >= 1.0
- pgvector (for vector search in PostgreSQL)

---

## Success Criteria

1. `@tool` decorator returns PydanticAI `Tool` objects directly
2. Agent functions receive PydanticAI `Tool` objects, no wrapping needed
3. AgentConfig stores tool registry slugs in `parameters`
4. Resolution handles both DB models and tool registry lookups
5. Collections integrate seamlessly as a dependency type
6. Changing DB config (collections, prompt, provider, tools) affects runtime behavior
7. All agents automatically get REST endpoints

---

## Migration Path

| Current | New |
|---------|-----|
| Agent model (mixed config + impl reference + search_enabled + allowed_collections) | AgentConfig (wiring) + Prompt + LLMProvider + Collection (pure config) |
| Hardcoded agent logic | Code-defined via @agent decorator |
| Implicit dependencies | Explicit type-hinted dependencies |
| Tools as plain functions | Tools as PydanticAI Tool objects via @tool |
| allowed_collections M2M | collections as a parameter in AgentConfig.parameters |
