# Agent Plane - User Stories

## Milestone 0 - PoC

- [x] Admins can create a new agent by specifying a system prompt
- [x] Users can prompt their agent through the web UI
    - [x] LLM request can be sent
    - [x] Instructions are used when initiating an agent conversation
    - [x] The web UI is minimally styled
- [x] Developers can send a prompt via REST API and get the agent's response
- [ ] Both API and UI support multi-turn conversations
    - [x] Conversation history can be stored in the DB
    - [x] The web UI allows adding a new chat message to a conversation
    - [ ] The web UI shows new responses as they come in
    - [ ] The API supports polling for new message events
    - [ ] The API supports adding a new message to a conversation
- [ ] Developers can connect to a self-hosted LLM (e.g., Ollama)
    - [ ] Discover available models

## Milestone 1 - RAG in a box

- [ ] Developers can manage document collections through a REST API
- [ ] Newly uploaded documents get indexed automatically
- [ ] Agents have access to a tool to search a document database
