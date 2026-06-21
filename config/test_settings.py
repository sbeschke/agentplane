"""
Test settings for django-mops project.
Uses SQLite and disables pgvector-specific features for testing.
"""

from .settings import *

# Use SQLite for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable pgvector for testing
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django.contrib.postgres"]

# Skip pgvector migrations
MIGRATION_MODULES = {
    "mops": "mops.migrations_test",
}
