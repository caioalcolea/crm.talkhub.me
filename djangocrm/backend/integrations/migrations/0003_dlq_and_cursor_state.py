"""
Add DLQ fields to WebhookLog for dead letter queue support,
and cursor_state to SyncJob for resumable sync.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0002_webhook_token"),
    ]

    operations = [
        # DLQ fields on WebhookLog
        migrations.AddField(
            model_name="webhooklog",
            name="is_dlq",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="webhooklog",
            name="retry_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="webhooklog",
            name="error_detail",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="webhooklog",
            name="can_retry",
            field=models.BooleanField(default=True),
        ),
        # Cursor state on SyncJob
        migrations.AddField(
            model_name="syncjob",
            name="cursor_state",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Estado do cursor para retomada. Ex: {'page': 15, 'status': 'open'}",
            ),
        ),
    ]
