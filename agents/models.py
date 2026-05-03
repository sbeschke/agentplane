from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

from django.db import models


class Agent(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    instructions = models.TextField(blank=True, null=True)
    llm_provider = models.ForeignKey(
        "LLMProvider",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="LLM provider for this agent",
    )
    model_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Model name to use (must be available in the selected provider)",
    )

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.llm_provider and self.model_name:
            if self.model_name not in self.llm_provider.available_models:
                raise ValidationError(
                    f"Model '{self.model_name}' is not available in provider '{self.llm_provider.name}'. "
                    f"Available models: {', '.join(self.llm_provider.available_models)}"
                )


class Conversation(models.Model):
    """Model to store conversations with agents. Each conversation is linked to a specific agent and contains a list of events (messages, responses, etc.).

    Events are stored in a JSONField as a list of dictionaries, where each dictionary represents an event. The format follows the PydanticAI format.
    """

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="conversations"
    )
    history = models.JSONField(
        default=list
    )  # Store the conversation history as a list of PydanticAI messages in JSON format
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation with {self.agent.name} at {self.created_at}"

    def get_history(self) -> list[ModelMessage]:
        """Get the conversation history as a list of ModelMessage objects."""
        return ModelMessagesTypeAdapter.validate_python(self.history)

    def set_history(self, messages: list[ModelMessage]):
        """Set the conversation history."""
        self.history = to_jsonable_python(messages)
        self.save()


class LLMProvider(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(
        help_text="Base URL for the LLM provider (e.g., http://localhost:11434/v1 for Ollama)"
    )
    available_models = models.JSONField(
        default=list, help_text="List of available model names"
    )
    last_discovered = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
