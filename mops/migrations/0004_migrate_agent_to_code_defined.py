# Generated migration for migrating Agent to code-defined agents

from django.db import migrations


def migrate_agent_to_prompt_and_config(apps, schema_editor):
    """Migrate existing Agent instances to Prompt + AgentConfig."""
    Agent = apps.get_model("mops", "Agent")
    Prompt = apps.get_model("mops", "Prompt")
    AgentConfig = apps.get_model("mops", "AgentConfig")

    for agent in Agent.objects.all():
        # Create Prompt from Agent
        prompt_slug = agent.slug or f"prompt-{agent.id}"
        Prompt.objects.create(
            slug=prompt_slug,
            name=agent.name,
            text=agent.instructions or "",
            description=agent.description or "",
        )

        # Create AgentConfig
        config_slug = agent.slug or f"config-{agent.id}"
        params = {"prompt": prompt_slug}

        if agent.llm_provider:
            params["llm"] = agent.llm_provider.slug

        # Handle search_enabled and allowed_collections
        # For migrated agents, we'll use the legacy_agent implementation
        # which expects collections as a list
        if agent.search_enabled and agent.allowed_collections.exists():
            params["collections"] = [c.slug for c in agent.allowed_collections.all()]

        AgentConfig.objects.create(
            slug=config_slug,
            name=agent.name,
            description=agent.description or "",
            implementation="legacy_agent",
            parameters=params,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("mops", "0003_add_code_defined_models"),
    ]

    operations = [
        migrations.RunPython(migrate_agent_to_prompt_and_config, migrations.RunPython.noop),
    ]
