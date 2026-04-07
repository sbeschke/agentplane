# Agent Plane - Architecture

## PoC

- Django + Django Admin for data management and record keeping
- SQLite storage
- Minimalistic, server-driven frontend with Django and HTMX
- Rest API via Django Ninja
- Pydantic AI for agentic logic
- Django Tasks with django-tasks-db for asynchronous tasks

### Classes

- `Agent`: Agents are defined through an "instructions" prompt. Must additionally have a name and slug.
- `Conversation`: Represents a multi-turn interaction with an agent. Stores the interaction's history in the form of events.
