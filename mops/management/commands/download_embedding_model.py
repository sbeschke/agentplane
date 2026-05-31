"""Management command to pre-download the embedding model."""

from django.core.management.base import BaseCommand

from mops.services import get_embedding_model


class Command(BaseCommand):
    help = "Pre-download the sentence-transformers embedding model"

    def handle(self, *args, **options):
        self.stdout.write("Downloading all-MiniLM-L6-v2 embedding model...")
        try:
            model = get_embedding_model()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded model: {model.get_sentence_embedding_dimension()} dimensions"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error downloading model: {e}"))
