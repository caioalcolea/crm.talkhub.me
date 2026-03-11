"""
Add webhook_token to IntegrationConnection for secure per-connection webhook URLs.

Three-step migration:
1. Add field without unique constraint (allows empty defaults)
2. Populate tokens for existing rows (bypasses RLS with raw SQL)
3. Add unique constraint
"""

import secrets

from django.db import migrations, models


def generate_tokens(apps, schema_editor):
    """Generate unique webhook tokens for all existing IntegrationConnection rows.

    Temporarily disables RLS so we can update all rows regardless of org context.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # Disable RLS so migration can see/update all rows (crm_user owns the table)
        cursor.execute("ALTER TABLE integration_connection DISABLE ROW LEVEL SECURITY")
        try:
            cursor.execute(
                "SELECT id FROM integration_connection "
                "WHERE webhook_token = '' OR webhook_token IS NULL"
            )
            rows = cursor.fetchall()
            for (row_id,) in rows:
                token = secrets.token_urlsafe(32)
                cursor.execute(
                    "UPDATE integration_connection SET webhook_token = %s WHERE id = %s",
                    [token, str(row_id)],
                )
        finally:
            # Re-enable RLS
            cursor.execute("ALTER TABLE integration_connection ENABLE ROW LEVEL SECURITY")


def reverse_tokens(apps, schema_editor):
    """Reverse: clear all webhook tokens."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("UPDATE integration_connection SET webhook_token = ''")


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        # Step 1: Add field without unique constraint
        migrations.AddField(
            model_name="integrationconnection",
            name="webhook_token",
            field=models.CharField(
                blank=True,
                default="",
                db_index=True,
                help_text="Token único para identificação do webhook. Auto-gerado.",
                max_length=64,
            ),
        ),
        # Step 2: Populate tokens for existing rows
        migrations.RunPython(generate_tokens, reverse_tokens),
        # Step 3: Add unique constraint
        migrations.AlterField(
            model_name="integrationconnection",
            name="webhook_token",
            field=models.CharField(
                blank=True,
                default="",
                db_index=True,
                help_text="Token único para identificação do webhook. Auto-gerado.",
                max_length=64,
                unique=True,
            ),
        ),
    ]
