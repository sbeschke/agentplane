# Agent Plane - Architecture

- Django + Django Admin for data management and record keeping
- PostgreSQL for Django application data; **pgvector** extension for vector embeddings (same database)
- Minimalistic, server-driven frontend with Django and HTMX
- REST API via Django Ninja
- Pydantic AI for agentic logic
- Django Tasks with django-tasks-db for asynchronous tasks

## Models

- `Agent`: Agents are defined through an "instructions" prompt. Must additionally have a name and slug.
    - Agents may be linked to an `LLMProvider` describing how AI responses may be generated.
    - Document search can be configured per agent, including which `Collection` records the agent may query.
- `Conversation`: Represents a multi-turn interaction with an agent. Stores the interaction's history in the form of events.
- `LLMProvider`: Describes an AI backend that may be used by an agent.
- `Collection`: Manages a set of documents that is automatically indexed and can be queried.
- `Document`: Element of a collection that stores and describes the input file that was indexed.
