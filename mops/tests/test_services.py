from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import TestCase, override_settings
from mops.models import Agent, Conversation, LLMProvider
from mops.services import discover_models, chat
from mops.conf import get_openai_compat_api_key, get_local_llm_base_url, get_local_llm_model


class DiscoverModelsTest(TestCase):
    def setUp(self):
        self.provider = LLMProvider.objects.create(
            name="Test provider",
            url="http://localhost:11434/v1",
            available_models=[],
        )

    @patch("mops.services.openai.OpenAI")
    def test_discover_models_updates_provider(self, mock_openai_class):
        """Test that discover_models successfully discovers and stores models."""
        # Mock the OpenAI client and its models list
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create mock model objects
        mock_model_1 = MagicMock()
        mock_model_1.id = "llama2"
        mock_model_2 = MagicMock()
        mock_model_2.id = "mistral"

        mock_models_response = MagicMock()
        mock_models_response.data = [mock_model_1, mock_model_2]
        mock_client.models.list.return_value = mock_models_response

        # Call the function
        result = discover_models(self.provider)

        # Check results
        self.assertEqual(result, ["llama2", "mistral"])
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.available_models, ["llama2", "mistral"])
        self.assertIsNotNone(self.provider.last_discovered)

    @patch("mops.services.openai.OpenAI")
    def test_discover_models_handles_connection_error(self, mock_openai_class):
        """Test that discover_models gracefully handles connection errors."""
        # Create a new provider for this test
        provider = LLMProvider.objects.create(
            name="Failing provider",
            url="http://invalid:11434/v1",
            available_models=[],
        )

        # Mock the OpenAI client to raise an exception
        mock_openai_class.side_effect = Exception("Connection failed")

        # Call the function
        result = discover_models(provider)

        # Should return empty list on error
        self.assertEqual(result, [])
        provider.refresh_from_db()
        # Models should not be updated
        self.assertEqual(provider.available_models, [])

    @patch("mops.services.openai.OpenAI")
    def test_discover_models_uses_correct_url(self, mock_openai_class):
        """Test that discover_models uses the provider's URL."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_models_response = MagicMock()
        mock_models_response.data = []
        mock_client.models.list.return_value = mock_models_response

        discover_models(self.provider)

        # Check that OpenAI client was created with the correct URL
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        self.assertEqual(call_kwargs["base_url"], "http://localhost:11434/v1")
        self.assertEqual(call_kwargs["api_key"], get_openai_compat_api_key())


class ChatTest(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(
            name="Test Agent",
            slug="test-agent",
            instructions="Be helpful.",
        )
        self.conversation = Conversation.objects.create(agent=self.agent, history=[])

    @patch("mops.services.Agent")
    @patch("mops.services.OpenAIChatModel")
    @patch("mops.services.OpenAIProvider")
    def test_chat_with_provider_and_model(
        self, mock_provider_class, mock_model_class, mock_agent_class
    ):
        """Test that chat uses the provider and model when available."""
        # Set up the agent with provider and model
        self.provider = LLMProvider.objects.create(
            name="Test provider",
            url="http://localhost:11434/v1",
            available_models=["llama2", "mistral"],
        )
        self.agent.llm_provider = self.provider
        self.agent.model_name = "llama2"
        self.agent.save()

        # Mock the provider, model, and agent
        mock_provider_instance = MagicMock()
        mock_provider_class.return_value = mock_provider_instance

        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the result
        mock_result = MagicMock()
        mock_result.all_messages.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_agent_instance.run_sync.return_value = mock_result

        # Call chat
        chat(self.conversation, "Hello")

        # Verify OpenAI-compatible provider was created with correct URL
        mock_provider_class.assert_called_once_with(
            base_url=self.provider.url,
            api_key=get_openai_compat_api_key(),
        )

        # Verify OpenAIChatModel was created with correct model and provider
        mock_model_class.assert_called_once_with(
            "llama2", provider=mock_provider_instance
        )

        # Verify Agent was created with the model and instructions
        mock_agent_class.assert_called_once()
        agent_call_kwargs = mock_agent_class.call_args.kwargs
        self.assertEqual(agent_call_kwargs["instructions"], self.agent.instructions)

        # Verify run_sync was called
        mock_agent_instance.run_sync.assert_called_once()

        # Verify conversation history was updated
        self.conversation.refresh_from_db()
        self.assertEqual(len(self.conversation.history), 2)

    @override_settings(
        MOPS_LOCAL_LLM_BASE_URL="http://127.0.0.1:9/v1",
        MOPS_LOCAL_LLM_MODEL="fallback-model",
    )
    @patch("mops.services.OpenAIProvider")
    @patch("mops.services.OpenAIChatModel")
    @patch("mops.services.Agent")
    def test_chat_without_provider_uses_fallback(
        self, mock_agent_class, mock_model_class, mock_provider_class
    ):
        """Test that chat falls back to bundled local llama-server settings."""
        mock_provider_instance = MagicMock()
        mock_provider_class.return_value = mock_provider_instance
        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        mock_result = MagicMock()
        mock_result.all_messages.return_value = []
        mock_agent_instance.run_sync.return_value = mock_result

        chat(self.conversation, "Hello")

        mock_provider_class.assert_called_once_with(
            base_url="http://127.0.0.1:9/v1",
            api_key=get_openai_compat_api_key(),
        )
        mock_model_class.assert_called_once_with(
            "fallback-model", provider=mock_provider_instance
        )
        mock_agent_class.assert_called_once()
        agent_call_kwargs = mock_agent_class.call_args.kwargs
        self.assertEqual(agent_call_kwargs["instructions"], self.agent.instructions)

    @patch("mops.services.Agent")
    def test_chat_handles_error_gracefully(self, mock_agent_class):
        """Test that chat handles errors gracefully."""
        # Mock the agent to raise an exception
        mock_agent_class.side_effect = Exception("Model error")

        # Call chat - should not raise
        chat(self.conversation, "Hello")

        # Conversation should still exist and be accessible
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.id, self.conversation.id)

    @patch("mops.services.Agent")
    @patch("mops.services.OpenAIChatModel")
    @patch("mops.services.OpenAIProvider")
    def test_chat_updates_conversation_history(
        self, mock_provider_class, mock_model_class, mock_agent_class
    ):
        """Test that chat properly updates conversation history."""
        # Set up the agent with provider and model
        self.provider = LLMProvider.objects.create(
            name="Test provider",
            url="http://localhost:11434/v1",
            available_models=["llama2"],
        )
        self.agent.llm_provider = self.provider
        self.agent.model_name = "llama2"
        self.agent.save()

        # Mock the components
        mock_provider_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock multiple messages in the result
        test_messages = [
            {"role": "user", "content": [{"type": "text", "text": "Hi"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Hello!"}]},
            {"role": "user", "content": [{"type": "text", "text": "How are you?"}]},
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'm doing well!"}],
            },
        ]

        mock_result = MagicMock()
        mock_result.all_messages.return_value = test_messages
        mock_agent_instance.run_sync.return_value = mock_result

        # Call chat
        chat(self.conversation, "Hi")

        # Verify conversation history was updated correctly
        self.conversation.refresh_from_db()
        self.assertEqual(len(self.conversation.history), 4)
        self.assertEqual(self.conversation.history, test_messages)
