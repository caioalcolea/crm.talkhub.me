"""Translate English stage names to pt-BR for existing opportunity pipelines."""

from django.db import migrations


NAME_MAP = {
    "Prospecting": "Prospecção",
    "Qualification": "Qualificação",
    "Proposal": "Proposta",
    "Negotiation": "Negociação",
    "Closed Won": "Ganho",
    "Closed Lost": "Perdido",
}


def translate_stages(apps, schema_editor):
    OpportunityStage = apps.get_model("opportunity", "OpportunityStage")
    for old_name, new_name in NAME_MAP.items():
        stages = OpportunityStage.objects.filter(name=old_name)
        for stage in stages:
            if not OpportunityStage.objects.filter(pipeline=stage.pipeline, name=new_name).exists():
                stage.name = new_name
                stage.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("opportunity", "0003_enable_rls_pipeline"),
    ]

    operations = [
        migrations.RunPython(translate_stages, migrations.RunPython.noop),
    ]
