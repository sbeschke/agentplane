# Post-Migration Roadmap: Prompt-Based Agents

## Overview

After completing the django-mops-agents migration, evolve the architecture to:
1. Separate **Prompt** (configuration) from **Agent** (runtime)
2. Enable pure PydanticAI agents defined in code
3. Auto-generate endpoints from agent functions
4. Allow runtime prompt customization via DB
5. Use django-reversion for prompt history and versioning

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Code (agents.py)                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ @agent(slug="greeting-bot")                              │ │
│  │ def greeting_agent() -> Agent:                            │ │
│  │     return Agent(instructions="Be friendly")              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   mops/registry.py                            │
│  - Discovers @agent decorated functions                       │
│  - Maps slugs to agent factories                              │
│  - Generates OpenAPI schema from PydanticAI Agent            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Prompt Model   │ │  Agent Runtime   │ │  Endpoint        │
│  (DB-stored)     │ │  (PydanticAI)    │ │  Generator       │
│  - slug          │ │  - Executes      │ │  - /agents/{slug}│
│  - name          │ │    agent runs    │ │  - POST /run     │
│  - instructions  │ │  - Manages state │ │  - GET /status   │
│  - model_name    │ │  - Handles tools │ │  - WebSocket     │
│  - llm_provider  │ │                 │ │  (optional)     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Runtime Flow                                 │
│  1. Request → /agents/greeting-bot                            │
│  2. Look up Prompt by slug from DB                            │
│  3. Call agent factory: greeting_agent()                      │
│  4. Inject Prompt.instructions into Agent                    │
│  5. Execute and return response                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase A: Prompt Model Migration (Week 1)

### Tasks
- [ ] Add `django-reversion` to dependencies
- [ ] Create new `Prompt` model (replaces `Agent` model)
  ```python
  @reversion.register()
  class Prompt(models.Model):
      slug = models.SlugField(unique=True)
      name = models.CharField(max_length=255)
      description = models.TextField(blank=True)
      instructions = models.TextField()
      model_name = models.CharField(max_length=255, null=True, blank=True)
      llm_provider = models.ForeignKey(
          "LLMProvider",
          on_delete=models.SET_NULL,
          null=True,
          blank=True,
      )
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
  ```
- [ ] Register `Prompt` with django-reversion in `apps.py`
- [ ] Add migration to transfer existing Agent data to Prompt
- [ ] Remove old `Agent` model (no backwards compatibility needed)
- [ ] Add `Prompt.get_latest(slug)` class method helper
- [ ] Update admin interface to use `Prompt`
- [ ] Add `mops.get_prompt(slug)` utility function
- [ ] Run tests, verify data migration

### Deliverables
- `Prompt` model exists with django-reversion support
- Existing agents migrated to prompts
- Admin interface works with new model
- Users can revert to previous prompt versions via django-reversion UI

---

## Phase B: Pure PydanticAI Agents (Week 2)

### Tasks
- [ ] Create `mops/agents.py` with agent factory support:
  ```python
  from pydantic_ai import Agent as PydanticAgent
  from typing import Callable

  AgentFactory = Callable[[], PydanticAgent]
  ```
- [ ] Create `@agent` decorator to register factories:
  ```python
  _registry: dict[str, AgentFactory] = {}

  def agent(slug: str, name: str = None, description: str = None):
      def decorator(func: AgentFactory):
          _registry[slug] = func
          return func
      return decorator
  ```
- [ ] Create `mops.get_agent(slug: str, conversation: Conversation = None) -> Agent`
    - Looks up `Prompt` by slug (latest version)
    - Calls registered factory
    - Overrides with `Prompt` data (instructions, model, provider)
    - Returns ready-to-use Agent
- [ ] Update existing services to use new agent resolution
- [ ] Run tests

### Deliverables
- Pure PydanticAI agents work via `@agent` decorator
- Prompt data from DB overrides code-defined defaults at runtime
- Agent registry is functional

---

## Phase C: Endpoint Generation (Week 3)

### Tasks
- [ ] Create `mops/endpoints.py` with endpoint generators:
  ```python
  from ninja import Router

  def create_agent_router(slug: str) -> Router:
      router = Router()

      @router.post("/")
      def run_agent(request, message: str):
          agent = get_agent(slug)
          conversation = create_conversation(slug)
          result = agent.run(message)
          return {"response": result}

      @router.get("/")
      def get_agent_info(request):
          prompt = get_prompt(slug)
          return {"name": prompt.name, "description": prompt.description}

      return router
  ```
- [ ] Create `mops/urls.py` that auto-discovers and registers endpoints:
  ```python
  from ninja import NinjaAPI
  from mops.registry import get_registered_agents

  api = NinjaAPI()

  for slug in get_registered_agents():
      router = create_agent_router(slug)
      api.add_router(f"/agents/{slug}/", router)
  ```
- [ ] Allow users to customize URL prefix via settings:
  ```python
  MOPS_URL_PREFIX = "agents/"  # default
  ```
- [ ] Add endpoint for listing all available agents (`GET /agents/`)
- [ ] Run tests

### Deliverables
- Endpoints auto-generated from `@agent` decorated functions
- Users can include via `path("mops/", include("mops.urls"))`
- Customizable URL prefix via settings
- All agents automatically get REST endpoints

---

## Phase D: Utility Functions (Week 3)

### Tasks
- [ ] `mops.get_prompt(slug: str) -> Prompt`
    - Get latest prompt from DB by slug
- [ ] `mops.get_agent(slug: str, conversation: Conversation = None) -> Agent`
    - Get or create agent from prompt + factory
- [ ] `mops.list_agents() -> list[AgentMetadata]`
    - List all registered agents with metadata
- [ ] `mops.create_conversation(agent_slug: str) -> Conversation`
    - Helper to start a conversation
- [ ] Add type hints and docstrings
- [ ] Run tests

### Deliverables
- Clean, documented utility API
- Easy integration for users

---

## Example: Complete User Experience

```python
# myproject/agents.py
from mops import agent, Agent, Tool

@agent(slug="weather-bot", name="Weather Assistant")
def weather_agent():
    def get_weather(city: str) -> str:
        return f"Sunny in {city}"

    return Agent(
        instructions="You are a weather assistant.",
        tools=[Tool(get_weather)],
    )

@agent(slug="chat-bot")
def chat_agent():
    return Agent(instructions="You are a helpful assistant.")
```

```python
# myproject/urls.py
from django.urls import path, include

urlpatterns = [
    path("api/", include("mops.urls")),  # Auto-generates endpoints
]
```

```python
# User code to interact
from mops import get_agent, get_prompt, create_conversation

# Get the agent (uses DB prompt if overridden)
agent = get_agent("weather-bot")

# Or get the prompt directly
prompt = get_prompt("weather-bot")
print(prompt.instructions)  # May have been edited in admin

# Start a conversation
conversation = create_conversation("weather-bot")
```

---

## Authentication

Authentication is handled via Django's middleware system. Users can:

1. **Use Django's built-in auth**: Apply `@login_required` or `@permission_required` decorators
2. **Use Ninja's auth**: Pass auth dependencies to endpoints
3. **Wrap URLs**: Apply custom middleware to mops URLs

Example with Ninja auth:
```python
# In consuming project's api.py
from ninja.security import HttpBearer
from mops.endpoints import create_agent_router

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        # Custom auth logic
        ...

# Apply to all mops endpoints
for slug in get_registered_agents():
    router = create_agent_router(slug)
    for operation in router.operations:
        operation.auth = AuthBearer()
    api.add_router(f"/agents/{slug}/", router)
```

---

## Prompt Versioning with django-reversion

### How It Works

- Every save to a `Prompt` creates a new revision
- Users can revert to any previous version via admin UI or programmatically
- All history is preserved - reverting creates a new version that matches the old one

### Usage

```python
import reversion
from reversion.models import Version
from mops.models import Prompt

# Get a prompt
prompt = Prompt.objects.get(slug="weather-bot")

# Get all versions of a prompt
versions = Version.objects.get_for_object(prompt)

# Revert to a specific version
reversion.revert(versions[2])  # Restore 3rd version

# Get latest version (helper method)
prompt = Prompt.get_latest("weather-bot")
```

### Admin Integration

With django-reversion installed, the Prompt admin automatically includes:
- A "History" button in the sidebar
- List of all versions with timestamps and user
- "Revert" button to restore any version

---

## Migration Path Summary

```
Current State                    Post-Migration               Future State
───────────────────────────────────────────────────────────────────────────
Agent model (code + config)  →  Prompt model (config only)  →  Prompt model
Agent class (Django)         →  Agent class (mops)          →  Pure PydanticAI
Manual URL definition        →  Merged into mops/          →  Auto-generated
Hardcoded agents             →  DB-configurable            →  Code-defined + DB override
No versioning                →  django-reversion           →  Full history + revert
```

---

## Dependencies

### Required (new)
- django-reversion >= 5.0

### Existing (carried forward)
- Django >= 6.0
- pydantic-ai >= 0.0.12
- ninja-api >= 1.0
- openai >= 1.0
- django-tasks >= 0.11

### Optional
- pgvector (for vector search in PostgreSQL)
- psycopg2-binary or psycopg (for PostgreSQL)

---

## Success Criteria

1. **Prompt model**: `Prompt` model with django-reversion support works
2. **Agent registration**: `@agent` decorator registers functions
3. **Runtime override**: DB prompts override code defaults
4. **Endpoint generation**: Agents automatically get REST endpoints
5. **Versioning**: Users can revert prompts via admin UI
6. **Authentication**: Works with Django's middleware system
7. **Tests**: All tests pass

---

## Timeline Summary

| Phase | Duration | Focus |
|-------|----------|-------|
| A | Week 1 | Prompt model with django-reversion |
| B | Week 2 | Pure PydanticAI agents + registry |
| C | Week 3 | Endpoint auto-generation |
| D | Week 3 | Utility functions |

**Total estimated time: 3 weeks**
