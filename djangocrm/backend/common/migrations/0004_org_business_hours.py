"""
Add business_hours and channel_rate_limits fields to Org model.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0003_disable_rls_pending_invitation"),
    ]

    operations = [
        migrations.AddField(
            model_name="org",
            name="business_hours",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Business hours config: {"timezone": "America/Sao_Paulo", '
                    '"windows": [{"days": [1,2,3,4,5], "start": "08:00", "end": "18:00"}]}'
                ),
            ),
        ),
        migrations.AddField(
            model_name="org",
            name="channel_rate_limits",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Per-channel hourly rate limits: {"smtp_native": 200, "talkhub_omni": 100}',
            ),
        ),
    ]
