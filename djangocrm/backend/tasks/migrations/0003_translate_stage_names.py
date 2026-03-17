"""Translate English stage names to pt-BR for existing task pipelines."""

from django.db import migrations


NAME_MAP = {
    "To Do": "A Fazer",
    "In Progress": "Em Andamento",
    "Review": "Revisão",
    "Done": "Concluído",
}


def translate_stages(apps, schema_editor):
    TaskStage = apps.get_model("tasks", "TaskStage")
    for old_name, new_name in NAME_MAP.items():
        stages = TaskStage.objects.filter(name=old_name)
        for stage in stages:
            if not TaskStage.objects.filter(pipeline=stage.pipeline, name=new_name).exists():
                stage.name = new_name
                stage.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0002_pipeline_visibility"),
    ]

    operations = [
        migrations.RunPython(translate_stages, migrations.RunPython.noop),
    ]
