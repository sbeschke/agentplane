# django_mops, a framework for model ops

mops is an easy, open and local-first programming framework for hosting your agents and LLM workflows on your own infrastructure. It helps Python developers build production agent systems without cloud dependencies.

You code your agents using PydanticAI, and mops provides API endpoints, session management, and more. It integrates with LLM servers or it can help you spin up an LLM with one command - all on your own infrastructure. No need to pay for cloud-based SaaS, no vendor lock-in, minimal boilerplate.

mops is batteries-included and provides support for the most essential building blocks of AI systems, such as prompt management, a RAG store, MCP support, and chat session management. However, mops is also extensible and allows you to define custom tools and workflows as you go along.

## Developer Experience

mops is the Django approach of agentic AI: It provides all essential functionality out of the box, but allows for infinite customisation without breaking out of its basic patterns. Developers use mops by starting a new Django project with the `django_mops` app enabled. They can then define their Pydantic agents in an `agents.py` file, registering them to the `django_mops` app using function decorators. The `django_mops` extension automatically creates endpoints that allow API users to interact with agents.

## Agent API

An agent session is created by sending a query to a JSON API endpoint. The agent's response can be observed in two distinct ways:

- Conversational: Returns all intermediate outputs by the agent including tool calls and results, and allows the user to add to the conversation by posting a response.
- Result: Waits for the agent to call a `Result` tool and returns only the argument passed by the agent. This allows developers to implement complex end-to-end tasks while hiding the details of the agent workflow from users.

## Small AI and Model Ops

Ultimately, `django_mops` will support the whole lifecycle of Small AI systems - including tracing, evaluation, collection of user feedback, and finetuning. By combining traces collected from users with feedback signals from evals, the framework should allow developers to set up regular training runs and serve models that are tuned to their specific workflows.

`django_mops` uses Django's `manage.py` pattern to provide helpers and templates for basic infrastructure setup, such as initializing project templates or spinning up a local LLM.
