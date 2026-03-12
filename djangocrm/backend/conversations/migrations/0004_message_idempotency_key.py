"""
Add idempotency_key field to Message model for robust anti-echo
and deduplication via UNIQUE constraint + IntegrityError catch.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversations", "0003_composite_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="idempotency_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Chave única para deduplicação. Format: {source}:{external_id}",
                max_length=128,
                null=True,
                unique=True,
            ),
        ),
    ]
