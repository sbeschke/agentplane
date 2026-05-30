# Migration Roadmap: Django → FastAPI + SQLModel

## Overview

**Goal**: Migrate from Django (Django ORM, Django Ninja, Django templates/HTMX) to FastAPI + SQLModel to achieve:
- Cleaner "import mopsai and go" developer experience
- API-first design with optional minimal demo frontend
- Lighter weight stack aligned with "FastAPI of agentic AI" vision
- No auth/users needed (simplifies migration significantly)

## Current Architecture

```
agentplane/
├── settings.py          # Django settings (DB, static, tasks)
├── urls.py              # URL routing to apps
├── asgi.py/wsgi.py      # ASGI/WSGI entry points
└── manage.py            # Django CLI

agents/
├── models.py            # Agent, Conversation, LLMProvider (Django ORM)
├── api.py               # REST API (Django Ninja)
├── views.py             # HTMX frontend views
├── urls.py              # Agent URL routing
├── services.py          # Agent execution, chat logic
├── admin.py             # Django Admin config
├── signals.py           # Django signals
└── migrations/          # Django migrations

documents/
├── models.py            # Collection, Document, DocumentChunk (Django ORM + pgvector)
├── api.py               # REST API (Django Ninja)
├── views.py             # HTMX frontend views
├── urls.py              # Document URL routing
├── services.py          # PDF extraction, chunking, embeddings, search
├── tasks.py             # Background tasks (django-tasks)
├── admin.py             # Django Admin config
├── signals.py           # Django signals
└── migrations/          # Django migrations
```

**Key dependencies**:
- Django 6.0.3 + Django Ninja (API) + Django templates
- django-tasks-db (background tasks)
- pgvector (PostgreSQL vector search)
- pydantic-ai (agents)
- sentence-transformers (embeddings)
- openai (LLM client)
- pypdf (PDF extraction)

## Target Architecture

```
mopsai/
├── __init__.py          # Package init, exports
├── main.py              # FastAPI app creation
├── config.py            # Settings/configuration
├── cli.py               # CLI entry point (replaces manage.py)
├── models/
│   ├── __init__.py
│   ├── agents.py        # Agent, Conversation, LLMProvider (SQLModel)
│   └── documents.py     # Collection, Document, DocumentChunk (SQLModel)
├── api/
│   ├── __init__.py
│   ├── agents.py         # Agent API routes
│   └── documents.py     # Document API routes
├── services/
│   ├── __init__.py
│   ├── agents.py         # Agent execution, chat logic
│   └── documents.py      # PDF, chunking, embeddings, search
├── tasks/
│   └── __init__.py      # Background task queue (anyio)
└── db.py                # Database session, migrations setup
```

**New dependencies**:
- fastapi
- sqlmodel
- uvicorn (ASGI server)
- alembic (migrations)
- anyio (async background tasks)
- pgvector (still needed for vector search)
- pydantic-ai (keep)
- sentence-transformers (keep)
- openai (keep)
- pypdf (keep)

## Migration Strategy

### Phase 1: Foundation (Week 1)
Create new package structure alongside existing Django code.

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Create mopsai/ package skeleton | mopsai/__init__.py, mopsai/config.py | Low | Copy settings logic |
| Setup SQLModel base | mopsai/db.py | Medium | SQLAlchemy engine, Alembic config |
| Create CLI skeleton | mopsai/cli.py | Low | typer with init, dev, db commands |
| Port Agent models | mopsai/models/agents.py | Medium | SQLModel equivalents |
| Port Document models | mopsai/models/documents.py | Medium | SQLModel + pgvector |
| Create Alembic migrations | alembic/ | Low | Initial schema |
| Setup FastAPI app | mopsai/main.py | Low | App factory |

### Phase 2: Core API (Week 2)
Port REST API endpoints from Django Ninja to FastAPI.

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Port agent API | mopsai/api/agents.py | Medium | Conversation CRUD, chat |
| Port document API | mopsai/api/documents.py | Medium | Collection CRUD, upload |
| Setup API router | mopsai/api/__init__.py | Low | Mount all routes |
| Configure CORS | mopsai/main.py | Low | For frontend access |

### Phase 3: Services (Week 3)
Port business logic, removing Django-specific dependencies.

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Port agent services | mopsai/services/agents.py | Medium | Replace Django ORM with SQLModel |
| Port document services | mopsai/services/documents.py | High | Mostly reusable logic |
| Setup background tasks | mopsai/tasks/__init__.py | Medium | anyio-based queue |

### Phase 4: Configuration & CLI (Week 4)
Complete the developer experience.

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Port settings | mopsai/config.py | Medium | Environment variables |
| Complete CLI | mopsai/cli.py | Medium | Project init, dev server, db |
| Update pyproject.toml | pyproject.toml | Low | Remove Django, add FastAPI/SQLModel |
| Create project template | templates/project/ | Medium | Cookiecutter template |

### Phase 5: Cleanup (Week 5)
Remove old Django code after validation.

| Task | Files | Effort | Notes |
|------|-------|--------|-------|
| Remove Django apps | agents/, documents/ | Low | After tests pass |
| Remove Django project | agentplane/ | Low | After tests pass |
| Update mise.toml | mise.toml | Low | Change to uvicorn |
| Update process-compose | process-compose.yaml | Low | Update web command |
| Update README | README.md | Low | New setup instructions |

## Detailed File-by-File Changes

### Models: Django ORM → SQLModel

**agents/models.py → mopsai/models/agents.py**
- Agent: CharField → Field(sa_type=String)
- ForeignKey → Relationship + foreign_key Field
- JSONField → Field(sa_type=JSON)
- DateTimeField(auto_now_add=True) → created_at with default_factory

**documents/models.py → mopsai/models/documents.py**
- VectorField → Use pgvector's Vector type with SQLAlchemy
- FileField → Store as String path, handle uploads separately
- ManyToManyField → Link table with Relationship

### API: Django Ninja → FastAPI

**agents/api.py → mopsai/api/agents.py**
- NinjaAPI → APIRouter
- get_object_or_404 → session.exec(select(...)).first() with HTTPException
- Django request → FastAPI Depends
- UploadedFile → UploadFile

**documents/api.py → mopsai/api/documents.py**
- Same pattern as agents
- File upload: use FastAPI's native UploadFile

### Services: Django → Pure Python/SQLModel

**agents/services.py → mopsai/services/agents.py**
- Remove django_tasks.task decorators
- Replace Django model queries with SQLModel
- Keep pydantic-ai integration

**documents/services.py → mopsai/services/documents.py**
- extract_text_from_pdf: keep as-is
- chunk_text: keep as-is
- generate_embedding: keep as-is
- search_chunks: replace Django ORM with SQLModel + pgvector
- index_document: replace Django file storage

### Background Tasks: django-tasks → anyio

**documents/tasks.py → mopsai/tasks/__init__.py**
- Replace @django_tasks.task with async functions
- Use anyio task queue or direct async execution

### CLI: manage.py → mopsai/cli.py

```python
import typer
app = typer.Typer()

@app.command()
def dev():
    import uvicorn
    uvicorn.run("mopsai.main:app", reload=True)

@app.command()
def db_upgrade():
    # Run alembic upgrade
    pass
```

## Dependency Changes

**Remove:**
- django, django-ninja, django-tasks-db, dj-database-url

**Add:**
- fastapi, sqlmodel, uvicorn[standard], alembic, asyncpg, anyio, typer

**Keep:**
- pgvector, pydantic-ai, sentence-transformers, openai, pypdf

## Updated pyproject.toml

```toml
[project]
name = "mopsai"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "sqlmodel>=0.0.14",
    "uvicorn[standard]>=0.27.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pgvector>=0.3.0",
    "pydantic-ai>=0.8.1",
    "sentence-transformers>=3.0.0",
    "openai>=2.30.0",
    "pypdf>=4.0.0",
    "anyio>=4.0.0",
    "typer>=0.9.0",
]

[project.scripts]
mops = "mopsai.cli:app"
```

## Updated mise.toml

```toml
[tasks]
dev = "uv run uvicorn mopsai.main:app --reload --port 8000"
test = "uv run pytest"
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQLModel limitations | Low | Medium | Validate early with POC |
| pgvector + SQLModel integration | Medium | High | Research, test first |
| Async complexity | Medium | High | Start sync, add async later |
| Breaking functionality | Medium | High | Comprehensive tests |

## Next Steps

1. **POC**: Create minimal FastAPI + SQLModel app with Agent model + one endpoint
2. **Validate**: Test pgvector integration with SQLModel
3. **Decide**: Sync vs async approach
4. **Proceed**: If POC works, start Phase 1
