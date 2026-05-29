from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    name = "documents"

    def ready(self):
        # Import signals to register them
        import documents.signals  # noqa: F401
