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
mise run init  # Tools, Python deps, DB migrations, prek hooks, llama-server runtime (GPU-capable where supported), GGUF weights
```

When you run **`mise run dev`**, the stack starts **PostgreSQL** with the **pgvector** extension (via Docker; default host port **55432**, see `scripts/run-dev-postgres.sh` and **`AGENTPLANE_PG_PORT`**), plus **llama-server** (OpenAI-compatible API on port **8765**: **GPU** on typical Linux with Vulkan drivers or Apple Silicon via Metal; falls back to CPU when no GPU backend is available), the Django web server, and the background worker. Install **Docker** for the Postgres service. Set **`DATABASE_URL`** in `.env` (see `.env.sample`) to use Postgres instead of SQLite; if it is unset, Django keeps using **`db.sqlite3`** (fine for lightweight tests).

For the first Postgres-backed setup, bring the stack up (`mise run dev`) before **`mise run init`** migrations, **or** start only Postgres temporarily, **`mise run migrate`**, then start the rest—so Postgres is reachable when migrations run with **`DATABASE_URL`** set.

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
