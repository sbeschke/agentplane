# django-mops-agents

A Django app for hosting AI agents and LLM workflows. Build conversational agents with RAG (Retrieval-Augmented Generation) support, powered by local or cloud LLM providers.

**Local-first**: Designed to work seamlessly with self-hosted models (llama-server, vLLM, etc.) while also supporting cloud providers like OpenAI.

## Features

- **Agent Management**: Create and manage AI agents with custom instructions
- **Conversations**: Persistent chat history with agents
- **Document Collections**: Upload and index PDF documents for RAG
- **REST API**: Full API support via Django Ninja
- **Web UI**: Built-in templates for agent interaction
- **Background Tasks**: Async document processing with django-tasks
- **Optional Vector Search**: PostgreSQL + pgvector integration (optional)

## Quick Start

### Installation

```bash
pip install django-mops-agents
```

Or from source:

```bash
# Clone the repository
git clone https://github.com/your-org/django-mops-agents.git
cd django-mops-agents

# Install in development mode
uv sync --extra all
```

### Configuration

Add to your Django project's `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    ...
    "mops.apps.MopsConfig",
]
```

Include the URLs in your project's `urls.py`:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("mops/", include("mops.urls", namespace="mops")),
]
```

### Required Settings

```python
# settings.py

# Database (SQLite is fine for development)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Background tasks (required)
TASKS = {
    "default": {"BACKEND": "django_tasks_db.DatabaseBackend", "QUEUES": ["default"]}
}

# Media files (for document uploads)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

### LLM Configuration

```python
# Local LLM (llama-server compatible)
MOPS_LOCAL_LLM_BASE_URL = "http://127.0.0.1:8765/v1"  # Default
MOPS_LOCAL_LLM_MODEL = "gemma-2-2b-it"  # Default

# OpenAI-compatible API key (used for authentication)
MOPS_OPENAI_API_KEY = "sk-local-provider"  # Default for local providers

# Optional: Set a default agent
MOPS_DEFAULT_AGENT = "my-agent"  # Optional
```

### Run Migrations

```bash
python manage.py migrate
```

### Create an Agent

```python
from mops.models import Agent

Agent.objects.create(
    name="My Assistant",
    slug="my-assistant",
    instructions="You are a helpful AI assistant. Answer questions accurately.",
    model_name="gemma-2-2b-it",
)
```

## Usage

### Web Interface

Start your development server:

```bash
python manage.py runserver
```

Visit:
- `http://127.0.0.1:8000/mops/` - List all agents
- `http://127.0.0.1:8000/mops/agents/{slug}/` - Agent detail page
- `http://127.0.0.1:8000/mops/conversations/` - Conversation list

### REST API

#### Start a Conversation

```bash
POST /mops/api/agents/{agent_slug}/conversation/
```

#### Send a Message

```bash
POST /mops/api/agents/{agent_slug}/conversation/{conversation_id}/
Content-Type: application/json

{
  "message": "Hello, how are you?"
}
```

#### Get Conversation History

```bash
GET /mops/api/agents/{agent_slug}/conversation/{conversation_id}/
```

#### Document Collections

```bash
GET /mops/api/collections/                    # List collections
POST /mops/api/collections/{slug}/documents/  # Upload PDF document
GET /mops/api/collections/{slug}/documents/  # List documents
```

## Configuration Reference

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `MOPS_LOCAL_LLM_BASE_URL` | `http://127.0.0.1:8765/v1` | Base URL for local LLM API |
| `MOPS_LOCAL_LLM_MODEL` | `gemma-2-2b-it` | Default model name |
| `MOPS_OPENAI_API_KEY` | `sk-local-provider` | API key for OpenAI-compatible endpoints |
| `MOPS_DEFAULT_AGENT` | `None` | Default agent slug (optional) |
| `MOPS_URL_PREFIX` | `mops/` | URL prefix for all mops endpoints |

### Optional Dependencies

| Package | Purpose |
|---------|---------|
| `pgvector` | PostgreSQL vector search for embeddings |
| `psycopg[binary]` | PostgreSQL database adapter |
| `reportlab` | PDF text extraction (for tests) |
| `sentence-transformers` | Embedding model for vector search |

## Project Structure

```
mops/
├── __init__.py
├── models.py              # Agent, Conversation, Collection, Document, etc.
├── services.py            # Chat, search, document processing
├── api.py                 # REST API endpoints (Django Ninja)
├── urls.py                # URL routing
├── apps.py                # App configuration
├── admin.py               # Django admin registration
├── signals.py             # Signal handlers
├── conf/
│   └── __init__.py        # Configuration and settings
├── management/
│   └── commands/
│       └── mops_init.py    # Initialization command
├── templates/
│   └── mops/              # Web UI templates
└── migrations/           # Database migrations
```

## Running Tests

```bash
# Run all tests
python manage.py test mops.tests

# Run with SQLite (avoids PostgreSQL dependency)
DATABASE_URL="sqlite:///test.db" python manage.py test mops.tests
```

## Development

This project uses:
- **mise** for environment management
- **uv** for Python dependencies

### Setup

```bash
# Install mise and tools
mise install

# Install Python dependencies
mise x -- uv sync --extra all

# Run migrations
mise x -- uv run python manage.py migrate

# Run tests
mise x -- uv run python manage.py test mops.tests
```

### Commands

```bash
mise run dev      # Start development server
mise run format   # Format code and run linter
mise run test     # Run all tests
```

## License

MIT
