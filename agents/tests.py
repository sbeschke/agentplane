import json
from unittest.mock import patch

from django.test import TestCase

from agents.models import Agent


class StartConversationAPITest(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(
            name="Test Agent",
            slug="test-agent",
            instructions="Respond with a greeting.",
        )
        self.url = f"/api/agents/{self.agent.slug}/conversation/"

    @patch("agents.api.chat")
    def test_start_conversation_returns_response(self, mock_chat):
        mock_chat.return_value = "Hello from the agent"

        response = self.client.post(
            self.url,
            json.dumps({"message": "Hello"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "Hello from the agent"})
        mock_chat.assert_called_once_with(self.agent, "Hello")

    def test_start_conversation_unknown_agent_returns_404(self):
        response = self.client.post(
            "/api/agents/unknown/conversation/",
            json.dumps({"message": "Hello"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
