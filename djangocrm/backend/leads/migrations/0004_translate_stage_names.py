"""Translate English stage names to pt-BR for existing lead pipelines."""

from django.db import migrations


NAME_MAP = {
    "New": "Novo",
    "Contacted": "Contatado",
    "Qualified": "Qualificado",
    "Proposal": "Proposta",
    "Won": "Ganho",
    "Lost": "Perdido",
}


def translate_stages(apps, schema_editor):
    LeadStage = apps.get_model("leads", "LeadStage")
    for old_name, new_name in NAME_MAP.items():
        # Skip if target name already exists in same pipeline (avoid unique constraint)
        stages = LeadStage.objects.filter(name=old_name)
        for stage in stages:
            if not LeadStage.objects.filter(pipeline=stage.pipeline, name=new_name).exists():
                stage.name = new_name
                stage.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0003_pipeline_visibility"),
    ]

    operations = [
        migrations.RunPython(translate_stages, migrations.RunPython.noop),
    ]
