# mops/migrations/0002_vector_extension.py
from django.db import migrations
from pgvector.django import VectorExtension

class Migration(migrations.Migration):
    operations = [
        VectorExtension()
    ]