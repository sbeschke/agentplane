import json
from unittest.mock import patch

from django.test import TestCase

from agents.models import Agent, Conversation


class CreateConversationAPITest(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(
            name="Test Agent",
            slug="test-agent",
            instructions="Respond with a greeting.",
        )
        self.url = f"/api/agents/{self.agent.slug}/conversation/"

    def test_create_conversation_returns_details(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": Conversation.objects.first().id,
                "agent_slug": self.agent.slug,
                "history": [],
            },
        )
        self.assertEqual(Conversation.objects.count(), 1)

    def test_create_conversation_unknown_agent_returns_404(self):
        response = self.client.post(
            "/api/agents/unknown/conversation/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)


class AddMessageAPITest(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(
            name="Test Agent",
            slug="test-agent",
            instructions="Respond with a greeting.",
        )
        self.conversation = self.agent.conversations.create(history=[])
        self.url = f"/api/agents/{self.agent.slug}/conversation/{self.conversation.id}/"

    @patch("agents.api.chat")
    def test_add_message_schedules_chat(self, mock_chat):
        response = self.client.post(
            self.url,
            json.dumps({"message": "Hello"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        mock_chat.assert_called_once_with(self.conversation, "Hello")

    def test_add_message_for_wrong_agent_returns_404(self):
        other_agent = Agent.objects.create(
            name="Other Agent",
            slug="other-agent",
            instructions="Respond briefly.",
        )
        url = f"/api/agents/{other_agent.slug}/conversation/{self.conversation.id}/"

        response = self.client.post(
            url,
            json.dumps({"message": "Hello"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)


class GetConversationAPITest(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(
            name="Test Agent",
            slug="test-agent",
            instructions="Respond with a greeting.",
        )
        self.conversation = self.agent.conversations.create(
            history=[{"role": "user", "content": "Hello"}],
        )
        self.url = f"/api/agents/{self.agent.slug}/conversation/{self.conversation.id}/"

    def test_get_conversation_returns_history(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": self.conversation.id,
                "agent_slug": self.agent.slug,
                "history": [{"role": "user", "content": "Hello"}],
            },
        )

    def test_get_conversation_for_wrong_agent_returns_404(self):
        other_agent = Agent.objects.create(
            name="Other Agent",
            slug="other-agent",
            instructions="Respond briefly.",
        )
        url = f"/api/agents/{other_agent.slug}/conversation/{self.conversation.id}/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
