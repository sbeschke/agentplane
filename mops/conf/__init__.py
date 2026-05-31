"""Configuration and settings for django-mops-agents.

All settings can be overridden in the Django project's settings.py.
"""

from django.conf import settings


def get_url_prefix():
    """Get the URL prefix for mops endpoints."""
    return getattr(settings, "MOPS_URL_PREFIX", "mops/")


def get_local_llm_base_url():
    """Get the local LLM base URL from settings."""
    return getattr(settings, "MOPS_LOCAL_LLM_BASE_URL", "http://127.0.0.1:8765/v1")


def get_local_llm_model():
    """Get the local LLM model from settings."""
    return getattr(settings, "MOPS_LOCAL_LLM_MODEL", "gemma-2-2b-it")


def get_openai_compat_api_key():
    """Get the OpenAI-compatible API key from settings."""
    return getattr(settings, "MOPS_OPENAI_API_KEY", "sk-local-provider")


def get_default_agent_slug():
    """Get the default agent slug from settings."""
    return getattr(settings, "MOPS_DEFAULT_AGENT", None)


def is_pgvector_available():
    """Check if pgvector is installed and available.

    Returns:
        bool: True if pgvector is available, False otherwise
    """
    import importlib.util

    return importlib.util.find_spec("pgvector") is not None


def get_embedding_field_type():
    """Get the appropriate field type for storing embeddings.

    Returns:
        The field class to use for embedding fields (ArrayField or JSONField)
    """
    from django.db import models

    if is_pgvector_available():
        from django.contrib.postgres.fields import ArrayField

        return ArrayField(models.FloatField, size=384)
    return models.JSONField


# For backwards compatibility, keep module-level constants
# but they will be evaluated at import time
LOCAL_LLM_BASE_URL = get_local_llm_base_url()
LOCAL_LLM_MODEL = get_local_llm_model()
OPENAI_COMPAT_API_KEY = get_openai_compat_api_key()
DEFAULT_AGENT_SLUG = get_default_agent_slug()
