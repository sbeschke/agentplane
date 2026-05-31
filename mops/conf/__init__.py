"""Configuration and settings for django-mops-agents.

All settings can be overridden in the Django project's settings.py.
"""

from django.conf import settings


def get_local_llm_base_url():
    """Get the local LLM base URL from settings."""
    return getattr(
        settings, "MOPS_LOCAL_LLM_BASE_URL", "http://127.0.0.1:8765/v1"
    )


def get_local_llm_model():
    """Get the local LLM model from settings."""
    return getattr(settings, "MOPS_LOCAL_LLM_MODEL", "gemma-2-2b-it")


def get_openai_compat_api_key():
    """Get the OpenAI-compatible API key from settings."""
    return getattr(
        settings, "MOPS_OPENAI_API_KEY", "sk-local-provider"
    )


# For backwards compatibility, keep module-level constants
# but they will be evaluated at import time
LOCAL_LLM_BASE_URL = get_local_llm_base_url()
LOCAL_LLM_MODEL = get_local_llm_model()
OPENAI_COMPAT_API_KEY = get_openai_compat_api_key()
