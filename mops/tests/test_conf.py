"""Tests for mops configuration module."""

from django.test import TestCase, override_settings

from mops.conf import (
    get_local_llm_base_url,
    get_local_llm_model,
    get_openai_compat_api_key,
    get_default_agent_slug,
    is_pgvector_available,
    get_embedding_field_type,
)


class ConfigDefaultsTest(TestCase):
    """Test that configuration functions return correct defaults."""

    def test_get_local_llm_base_url_default(self):
        """Test default local LLM base URL."""
        url = get_local_llm_base_url()
        self.assertEqual(url, "http://127.0.0.1:8765/v1")

    def test_get_local_llm_model_default(self):
        """Test default local LLM model."""
        model = get_local_llm_model()
        self.assertEqual(model, "gemma-2-2b-it")

    def test_get_openai_compat_api_key_default(self):
        """Test default OpenAI-compatible API key."""
        api_key = get_openai_compat_api_key()
        self.assertEqual(api_key, "sk-local-provider")

    def test_get_default_agent_slug_default(self):
        """Test default agent slug is None."""
        slug = get_default_agent_slug()
        self.assertIsNone(slug)


class ConfigOverridesTest(TestCase):
    """Test that configuration can be overridden via Django settings."""

    @override_settings(MOPS_LOCAL_LLM_BASE_URL="http://custom:1234/v1")
    def test_override_local_llm_base_url(self):
        """Test overriding local LLM base URL."""
        url = get_local_llm_base_url()
        self.assertEqual(url, "http://custom:1234/v1")

    @override_settings(MOPS_LOCAL_LLM_MODEL="custom-model")
    def test_override_local_llm_model(self):
        """Test overriding local LLM model."""
        model = get_local_llm_model()
        self.assertEqual(model, "custom-model")

    @override_settings(MOPS_OPENAI_API_KEY="custom-key")
    def test_override_openai_api_key(self):
        """Test overriding OpenAI API key."""
        api_key = get_openai_compat_api_key()
        self.assertEqual(api_key, "custom-key")

    @override_settings(MOPS_DEFAULT_AGENT="my-agent")
    def test_override_default_agent_slug(self):
        """Test overriding default agent slug."""
        slug = get_default_agent_slug()
        self.assertEqual(slug, "my-agent")


class PgvectorAvailabilityTest(TestCase):
    """Test pgvector availability checks."""

    def test_is_pgvector_available(self):
        """Test that pgvector availability is detected correctly."""
        # This will return True or False based on whether pgvector is installed
        available = is_pgvector_available()
        self.assertIsInstance(available, bool)

    def test_get_embedding_field_type(self):
        """Test that embedding field type is returned correctly."""
        field_type = get_embedding_field_type()
        # Should return either a field class or JSONField
        # In SQLite, it should return JSONField
        # In PostgreSQL with pgvector, it would return a VectorField class
        self.assertIsNotNone(field_type)
