from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_initial"),
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskpipeline",
            name="visible_to_teams",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
                related_name="visible_task_pipelines",
                to="common.teams",
            ),
        ),
        migrations.AddField(
            model_name="taskpipeline",
            name="visible_to_users",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
                related_name="visible_task_pipelines",
                to="common.profile",
            ),
        ),
    ]
