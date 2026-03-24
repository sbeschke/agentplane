# Agent Plane - Architecture

## PoC

- Django
- SQLite storage
- No frontend - manage through Django Admin
- Rest API via Django Ninja
- instructor for LLM access

### Classes

- `Agent`: Contains an agent definition, defined through name + slug, stores a system prompt.
