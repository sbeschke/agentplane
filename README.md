# Agent Plane

Agent Plane is a Django application for **creating and running** AI agents. You define each agent with instructions (a system prompt) and the tools it may use, then call it from a **REST API** or through the bundled web UI.

**Local-first** is a core goal: run against self-hosted models with minimal friction, while still supporting third-party LLM providers when you need them. Document **collections** (RAG) let you attach indexed knowledge that agents can search, configured per agent.

For full scope and roadmap detail, see [docs/vision.md](docs/vision.md).

## Setup

We use [mise](https://mise.jdx.dev/) to set up tools.

Install `mise` to make the commands shown in this section available.

### Initialisation

Run this command before starting development:

```
mise run init  # Set up for development (install dependencies and install pre-commit hooks)
```

### Development Commands

```
mise run dev     # start development server
mise run test    # run unittests
mise run mmm     # make migrations and migrate
```

### Committing

```
mise run format  # lint and format
```
