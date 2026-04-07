from pydantic_ai import Agent

from agents import models


def chat(conversation: models.Conversation, message: str) -> str:
    """Chat with the agent and return the response text."""
    history = conversation.get_history()
    pydantic_agent = Agent(
        "mistral:mistral-small-latest",
        instructions=conversation.agent.instructions,
    )
    result = pydantic_agent.run_sync(message, message_history=history)
    conversation.set_history(result.all_messages())
    return result.output
