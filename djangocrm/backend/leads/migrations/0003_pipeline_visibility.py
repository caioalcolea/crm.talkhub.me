from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0002_fix_compaign_typo"),
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="leadpipeline",
            name="visible_to_teams",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
                related_name="visible_lead_pipelines",
                to="common.teams",
            ),
        ),
        migrations.AddField(
            model_name="leadpipeline",
            name="visible_to_users",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
                related_name="visible_lead_pipelines",
                to="common.profile",
            ),
        ),
    ]
