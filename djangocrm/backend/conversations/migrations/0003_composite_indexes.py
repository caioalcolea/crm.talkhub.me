"""
Add composite indexes for filtered + sorted queries:
- (org, status, -last_message_at) for status filter with sort
- (org, channel, -last_message_at) for channel filter with sort
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversations", "0002_conversation_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["org", "status", "-last_message_at"],
                name="conv_org_status_msg",
            ),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["org", "channel", "-last_message_at"],
                name="conv_org_chan_msg",
            ),
        ),
    ]
