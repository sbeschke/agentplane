# Agent Plane - Architecture

## PoC

- Django + Django Admin for data management and record keeping
- SQLite storage
- Minimalistic, server-driven frontend with Django and HTMX
- Rest API via Django Ninja
- Pydantic AI for agentic logic
- Django Tasks with django-tasks-db for asynchronous tasks

### Classes

- `Agent`: Contains an agent definition, defined through name + slug, stores a system prompt.
