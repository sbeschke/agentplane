# Agent Plane - Architecture

## PoC

- Django
- SQLite storage
- No frontend - manage through Django Admin
- Rest API via Django Ninja
- any-llm for LLM access
- Django Tasks with django-tasks-db for asynchronous tasks

### Classes

- `Agent`: Contains an agent definition, defined through name + slug, stores a system prompt.
