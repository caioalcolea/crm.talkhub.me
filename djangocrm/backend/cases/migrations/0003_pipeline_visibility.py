from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0002_initial"),
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="casepipeline",
            name="visible_to_teams",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
                related_name="visible_case_pipelines",
                to="common.teams",
            ),
        ),
        migrations.AddField(
            model_name="casepipeline",
            name="visible_to_users",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
                related_name="visible_case_pipelines",
                to="common.profile",
            ),
        ),
    ]
