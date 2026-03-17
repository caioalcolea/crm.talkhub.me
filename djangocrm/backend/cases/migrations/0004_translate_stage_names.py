"""Translate English stage names to pt-BR for existing case pipelines."""

from django.db import migrations


NAME_MAP = {
    "New": "Novo",
    "Assigned": "Atribuído",
    "In Progress": "Em Andamento",
    "Resolved": "Resolvido",
    "Rejected": "Rejeitado",
}


def translate_stages(apps, schema_editor):
    CaseStage = apps.get_model("cases", "CaseStage")
    for old_name, new_name in NAME_MAP.items():
        stages = CaseStage.objects.filter(name=old_name)
        for stage in stages:
            if not CaseStage.objects.filter(pipeline=stage.pipeline, name=new_name).exists():
                stage.name = new_name
                stage.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0003_pipeline_visibility"),
    ]

    operations = [
        migrations.RunPython(translate_stages, migrations.RunPython.noop),
    ]
