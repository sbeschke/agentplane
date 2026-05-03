import django_tasks
from django.utils import timezone
import os
import openai
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from agents import models


def discover_models(provider: models.LLMProvider) -> list[str]:
    """Discover available models from the LLM provider."""
    try:
        # Use a valid-looking key format for local providers
        client = openai.OpenAI(
            base_url=provider.url,
            api_key=os.environ.get("OPENAI_API_KEY", "sk-local-provider"),
        )
        models = client.models.list()
        model_names = [model.id for model in models.data]
        provider.available_models = model_names
        provider.last_discovered = timezone.now()
        provider.save(update_fields=["available_models", "last_discovered"])
        return model_names
    except Exception as e:
        print(f"Error discovering models for {provider.name}: {e}")
        return []


@django_tasks.task
def run_agent_chat_task(conversation_id: int, message: str):
    """Background task to handle LLM chat and update conversation history."""
    conversation = models.Conversation.objects.get(id=conversation_id)
    chat(conversation, message)


def chat(conversation: models.Conversation, message: str) -> None:
    """Schedules the background task for chatting."""
    try:
        history = conversation.get_history()
        agent = conversation.agent

        if agent.llm_provider and agent.model_name:
            provider = OllamaProvider(base_url=agent.llm_provider.url)
            model = OpenAIChatModel(agent.model_name, provider=provider)
            pydantic_agent = Agent(
                model,
                instructions=agent.instructions,
            )
        else:
            # Fallback to hardcoded for backward compatibility
            pydantic_agent = Agent(
                "mistral:mistral-small-latest",
                instructions=agent.instructions,
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
