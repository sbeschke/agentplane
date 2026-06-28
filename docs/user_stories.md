# django-mops - User Stories

## Milestone 0 - PoC

The goal of this milestone is to provide minimal conversational AI capabilities—both via a development web UI and a REST API—with **local-first** usage as a first-class path (default local model support when no provider is configured).

- [x] Admins can create a new agent by specifying a system prompt
- [x] Users can prompt their agent through the web UI
    - [x] LLM request can be sent
    - [x] Instructions are used when initiating an agent conversation
    - [x] The web UI is minimally styled
- [x] Developers can send a prompt via REST API and get the agent's response
- [x] Both API and UI support multi-turn conversations
    - [x] Conversation history can be stored in the DB
    - [x] The web UI allows adding a new chat message to a conversation
    - [x] The web UI shows new responses as they come in
    - [x] The API supports polling for new message events
    - [x] The API supports adding a new message to a conversation
- [x] Developers can configure the LLM provider to point to a self-hosted model (OpenAI-compatible API)
    - [x] Developers can create an LLM provider in the Admin backend
    - [x] Developers can specify a URL for an LLM provider to connect to
    - [x] The app can discover the available models for a provider
    - [x] The app stores the available models for each provider
- [x] Developers can configure the LLM provider and model name to use for each agent
- [x] A local LLM is started along with the dev server and used as a fallback when no LLM provider is configured for the agent.
    Default path so development can run without pointing agents at an external or admin-configured provider.

## Milestone 1 - RAG in a box

The vision of this milestone is to provide an all-in-one solution for setting up a RAG-based agent.
Users can set up document collections (via Django Admin for now), which are indexed and made available to agents through tool calls. **End-user collection management in the web app is out of scope** for this milestone; Admin-only is acceptable.

- [x] Developers can create document collections through Django Admin
    - [x] A PostgreSQL instance with the pgvector extension is started along with the dev server
    - [x] The app uses that database for Django data and for vector embeddings (pgvector)
    - [x] Collections can be created through Django Admin
- [x] Developers can list collections and retrieve collection details through the REST API
- [x] Developers can add documents to a collection through a REST API
- [x] Documents can be uploaded through Django Admin
    - [x] A PDF document can be uploaded to a collection via POST request
    - [x] The document content gets stored inside a Document object that is owned by the collection
- [x] Newly uploaded documents get indexed automatically
    - [x] After a document has been uploaded, a background job is started up that chunks the document and then indexes each chunk
- [x] Each agent can be configured with document search: whether the search tool is enabled and which collections that agent may query
- [x] When document search is enabled for an agent, the agent has access to a tool that searches only the collections configured for that agent

## Milestone 2 - Code-defined agents

The idea of this milestone is to make agent configuration more flexible. Currently, agents can only be customized by providing a prompt. After this milestone, users can configure agents through code, by writing a function that returns an Agent.
A design doc for this milestone is in [`code_defined_agents.md`](code_defined_agents.md).

**Definition of Done:** After implementing every story, the following must be true:
- The new functionality is covered by tests (unit and API-level)
- The new functionality is demonstrated by adding example code to the `mops-example` app.

- [x] Developers can write a function returning an Agent, and decorate it with @agent to make it accessible through an API
  - [x] An example `mops-example` app, which uses `mops`, contains an `agents.py` file that demonstrates the usage of agent functions
  - [x] Each registered agent automatically exposes REST endpoints at `/agents/{slug}/`
  - [x] Developers can list all available agents via `/agents/`
- [x] The Agent data model is renamed to Prompt and can be passed to an agent function as a dependency
  - [x] Migrate existing Agent instances to new Prompt + AgentConfig models
  - [x] Update Conversation to reference AgentConfig instead of Agent
  - [x] Backward compatibility removed (no productive usage yet)
- [x] Individual collections and lists of collections can be passed into an agent function as a dependency
- [x] LLMProvider can be passed to an agent function as a dependency
- [x] Developers can define tools as decorated functions and pass them into agent functions as a dependency
  - [x] Tools are registered as factories via @tool decorator
  - [x] ToolConfig model stores runtime parameters for parameterized tools
- [x] A built-in `search_documents` tool is available for RAG operations
- [x] Agent function signatures are validated against AgentConfig parameters at startup
  - [x] Invalid AgentConfig (missing slugs, type mismatches) returns clear errors
  - [x] Custom exceptions (DependencyNotFoundError, InvalidTypeError) for error handling
