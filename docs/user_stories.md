# Agent Plane - User Stories

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

- [ ] Developers can create document collections through Django Admin
    - [ ] A PostgreSQL instance with the pgvector extension is started along with the dev server
    - [ ] The app uses that database for Django data and for vector embeddings (pgvector)
    - [ ] Collections can be created through Django Admin
- [ ] Developers can list collections and retrieve collection details through the REST API
- [ ] Developers can add documents to a collection through a REST API
    - [ ] A PDF document can be uploaded to a collection via POST request
    - [ ] The document content gets stored inside a Document object that is owned by the collection
- [ ] Newly uploaded documents get indexed automatically
    - [ ] After a document has been uploaded, a background job is started up that chunks the document and then indexes each chunk
- [ ] Each agent can be configured with document search: whether the search tool is enabled and which collections that agent may query
- [ ] When document search is enabled for an agent, the agent has access to a tool that searches only the collections configured for that agent
