from pydantic_ai import Agent as PydanticAgent

from agents.models import Agent

def chat(agent: Agent, message: str) -> str:
    """Chat with the agent and return the response text."""
    pydantic_agent = PydanticAgent(
        "mistral:mistral-small-latest",
        instructions=agent.instructions,
    )
    result = pydantic_agent.run_sync(message)
    return result.output
