from unittest.mock import patch
from django.test import TestCase
from mops.models import Agent, Conversation
from mops.services import run_agent_chat_task


class TestAgentChatFlow(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(
            name="Test Agent",
            slug="test-app",
            instructions="Respond with a greeting.",
        )
        self.conversation = Conversation.objects.create(agent=self.agent)

    @patch("mops.services.Agent")
    def test_background_task_updates_history(self, mock_pydantic_agent):
        # Mock the PydanticAI agent behavior
        mock_instance = mock_pydantic_agent.return_value

        # Simulate a successful response
        class MockResult:
            def __init__(self):
                self.output = "Hello!"
                self.all_messages = lambda: [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "Hi"}],
                    },
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hello!"}],
                    },
                ]

        mock_instance.run_sync.return_value = MockResult()

        # Since we are in a test environment without a worker,
        # we call the underlying function directly instead of .delay()
        # The task decorator wraps the function, so we access the original via __wrapped__ if available
        # or just call it as is if django-tasks allows.
        # In many cases, calling the decorated function works for logic testing.
        run_agent_chat_task.call(self.conversation.id, "Hi")

        # Refresh from DB
        self.conversation.refresh_from_db()

        # Check if history was updated
        self.assertTrue(len(self.conversation.history) > 0)
