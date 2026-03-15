"""
Add soft-delete fields to Conversation and change contact FK from CASCADE to SET_NULL.

- is_deleted: boolean flag for soft-delete
- deleted_at: timestamp of deletion
- deleted_by: FK to Profile who deleted
- contact: changed from CASCADE to SET_NULL (null=True, blank=True)
- New composite index for is_deleted + last_message_at queries
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversations", "0004_message_idempotency_key"),
        ("common", "0001_initial"),
    ]

    operations = [
        # Soft-delete fields
        migrations.AddField(
            model_name="conversation",
            name="is_deleted",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="conversation",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="conversation",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deleted_conversations",
                to="common.profile",
            ),
        ),
        # Change contact FK from CASCADE to SET_NULL
        migrations.AlterField(
            model_name="conversation",
            name="contact",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="conversations",
                to="contacts.contact",
            ),
        ),
        # Composite index for soft-delete queries
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["org", "is_deleted", "-last_message_at"],
                name="conv_org_del_msg",
            ),
        ),
    ]
