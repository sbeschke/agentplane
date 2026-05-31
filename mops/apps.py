"""App configuration for django-mops-agents.

Merged from agents/apps.py and documents/apps.py.
"""

from django.apps import AppConfig


class MopsConfig(AppConfig):
    name = "mops"

    def ready(self):
        # Import signals to register them
        import mops.signals  # noqa: F401
