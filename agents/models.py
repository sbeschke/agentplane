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
    events = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation with {self.agent.name} at {self.created_at}"
    
    def add_event(self, event: dict):
        self.events.append(event)
        self.save()
