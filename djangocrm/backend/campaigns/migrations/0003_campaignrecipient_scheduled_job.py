import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0001_initial"),
        ("campaigns", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaignrecipient",
            name="scheduled_job",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="campaign_recipients",
                to="assistant.scheduledjob",
            ),
        ),
    ]
