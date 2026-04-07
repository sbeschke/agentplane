import json

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

    def __str__(self):
        return self.name


class Conversation(models.Model):
    """Model to store conversations with agents. Each conversation is linked to a specific agent and contains a list of events (messages, responses, etc.).

    Events are stored in a JSONField as a list of dictionaries, where each dictionary represents an event. The format follows the PydanticAI format.
    """
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='conversations')
    history = models.JSONField(default=list)  # Store the conversation history as a list of PydanticAI messages in JSON format
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
