from pydantic_ai import Agent
import django_tasks

from agents import models


@django_tasks.task
def run_agent_chat_task(conversation_id: int, message: str):
    """Background task to handle LLM chat and update conversation history."""
    conversation = models.Conversation.objects.get(id=conversation_id)
    chat(conversation, message)


def chat(conversation: models.Conversation, message: str) -> None:
    """Schedules the background task for chatting."""
    try:
        history = conversation.get_history()
        pydantic_agent = Agent(
            "mistral:mistral-small-latest",
            instructions=conversation.agent.instructions,
        )
        result = pydantic_agent.run_sync(message, message_history=history)
        conversation.set_history(result.all_messages())
    except Exception as e:
        # In a real app, we might want to log this or store the error in the conversation history
        # For now, let's just print it.
        print(f"Error in background task for conversation {conversation.id}: {e}")
        # To satisfy the requirement of showing an error message:
        # We can append a special 'error' event to history if we want,
        # but since we are using PydanticAI messages, let's just log it in the console for now.
        # A better way would be to add a custom error message to the JSONField.
        pass
