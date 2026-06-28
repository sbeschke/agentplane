# mops-example

This is an example Django project demonstrating the usage of code-defined agents with django-mops.

## Setup

1. Make sure you have the main django-mops package installed and set up.
2. Add this directory to your Python path or install it as a package.
3. Import the agents module to register the example agents:

```python
# In your Django project's urls.py or apps.py
import mops_example.agents  # noqa: F401
```

## Usage

### Load Fixtures

To populate your database with example agents, tools, and configurations:

```bash
python manage.py loaddata agents.yaml
```

This will create:
- 3 Prompts (simple, weather, RAG)
- 2 LLM Providers (local, OpenAI)
- 2 Collections (docs, manuals)
- 3 ToolConfigs (weather, calculator, search)
- 5 AgentConfigs (simple-bot, weather-bot, rag-bot, multi-tool-bot, kitchen-sink-bot)

### Access Agents via API

Once the fixtures are loaded, you can access the agents via the API:

- List all agents: `GET /api/agents/`
- Get agent info: `GET /api/agents/{slug}/`
- Run an agent: `POST /api/agents/{slug}/` with `{"message": "your message"}`

### Example Agent Configurations

1. **simple-bot**: A basic agent with just a prompt and LLM provider.
2. **weather-bot**: An agent that uses the weather tool.
3. **rag-bot**: A RAG agent that searches documents.
4. **multi-tool-bot**: An agent with multiple tools (weather + calculator).
5. **kitchen-sink-bot**: An agent with all possible dependencies.

## Note on uv Configuration

This example project is designed to work independently of the top-level uv configuration. It does not include its own pyproject.toml to avoid conflicts. Make sure to:

1. Use the same Python environment as the main project
2. Install all required dependencies (django, pydantic-ai, etc.)
3. Configure your database settings appropriately
