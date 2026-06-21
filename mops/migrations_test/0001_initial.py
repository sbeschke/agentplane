# Test migration - simplified version without pgvector dependencies

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='LLMProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(blank=True, max_length=255, null=True, unique=True)),
                ('url', models.URLField(help_text='Base URL for an OpenAI-compatible HTTP API (include /v1), e.g. http://127.0.0.1:8765/v1')),
                ('default_model', models.CharField(blank=True, default='', help_text='Default model to use for this provider', max_length=255)),
                ('available_models', models.JSONField(default=list, help_text='List of available model names')),
                ('last_discovered', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, null=True, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('instructions', models.TextField(blank=True, null=True)),
                ('model_name', models.CharField(blank=True, help_text='Model name to use (must be available in the selected provider)', max_length=255, null=True)),
                ('search_enabled', models.BooleanField(default=False, help_text='Enable document search tool for this agent')),
                ('llm_provider', models.ForeignKey(blank=True, help_text='LLM provider for this agent', null=True, on_delete=django.db.models.deletion.SET_NULL, to='mops.llmprovider')),
            ],
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('history', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='legacy_conversations', to='mops.agent')),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='documents/')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('original_filename', models.CharField(blank=True, max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('file_size', models.PositiveIntegerField(blank=True, help_text='Size in bytes', null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='mops.collection')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('chunk_index', models.PositiveIntegerField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='mops.document')),
            ],
            options={
                'ordering': ('document', 'chunk_index'),
            },
        ),
        migrations.CreateModel(
            name='AgentConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('implementation', models.CharField(help_text='Registered agent factory function name', max_length=255)),
                ('parameters', models.JSONField(default=dict, help_text="Dependency slugs for the agent (e.g., {'prompt': 'my-prompt', 'llm': 'openai'})")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Prompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('text', models.TextField()),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ToolConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('tool_slug', models.CharField(help_text="Registered tool factory name (e.g., 'search_documents')", max_length=255)),
                ('parameters', models.JSONField(default=dict, help_text="Runtime parameters for the tool factory (e.g., {'collections': ['docs']})")),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='conversation',
            name='agent_config',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversations', to='mops.agentconfig'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['collection', 'created_at'], name='mops_docume_collect_04bd70_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['id'], name='mops_docume_id_90026a_idx'),
        ),
        migrations.AddIndex(
            model_name='documentchunk',
            index=models.Index(fields=['document', 'chunk_index'], name='mops_docume_documen_fdbaa8_idx'),
        ),
        migrations.AddField(
            model_name='agent',
            name='allowed_collections',
            field=models.ManyToManyField(blank=True, help_text='Collections this agent can search', to='mops.collection'),
        ),
    ]
