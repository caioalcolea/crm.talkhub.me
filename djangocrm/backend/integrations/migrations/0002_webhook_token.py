"""
Add webhook_token to IntegrationConnection for secure per-connection webhook URLs.

Idempotent migration using raw SQL to handle dirty DB state from previous
failed attempts. Uses SeparateDatabaseAndState so Django tracks the field
correctly while we control the actual DDL.
"""

import secrets

from django.db import migrations, models


def add_column_and_populate(apps, schema_editor):
    """Idempotent: add webhook_token column, populate tokens, add unique constraint.

    Handles dirty DB state where column/indexes may already exist from
    previous failed migration attempts. Temporarily disables RLS so we can
    update all rows regardless of org context.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # Step 1: Add column if it doesn't exist
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'integration_connection'
                    AND column_name = 'webhook_token'
                ) THEN
                    ALTER TABLE integration_connection
                    ADD COLUMN webhook_token VARCHAR(64) NOT NULL DEFAULT '';
                END IF;
            END $$;
        """)

        # Step 2: Disable RLS so we can see/update all rows
        cursor.execute("ALTER TABLE integration_connection DISABLE ROW LEVEL SECURITY")
        try:
            # Step 3: Populate tokens for rows that don't have one
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
            # Step 4: Re-enable RLS
            cursor.execute("ALTER TABLE integration_connection ENABLE ROW LEVEL SECURITY")

        # Step 5: Drop orphaned indexes from previous failed attempts
        cursor.execute("""
            DROP INDEX IF EXISTS integration_connection_webhook_token_b2d0be75_like;
        """)
        cursor.execute("""
            DROP INDEX IF EXISTS integration_connection_webhook_token_b2d0be75;
        """)
        cursor.execute("""
            DROP INDEX IF EXISTS integration_connection_webhook_token_b2d0be75_uniq;
        """)

        # Step 6: Create the indexes fresh
        cursor.execute("""
            CREATE UNIQUE INDEX integration_connection_webhook_token_b2d0be75_uniq
            ON integration_connection (webhook_token);
        """)
        cursor.execute("""
            CREATE INDEX integration_connection_webhook_token_b2d0be75_like
            ON integration_connection (webhook_token varchar_pattern_ops);
        """)


def reverse_migration(apps, schema_editor):
    """Reverse: drop column entirely."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            DROP INDEX IF EXISTS integration_connection_webhook_token_b2d0be75_uniq;
        """)
        cursor.execute("""
            DROP INDEX IF EXISTS integration_connection_webhook_token_b2d0be75_like;
        """)
        cursor.execute("""
            ALTER TABLE integration_connection DROP COLUMN IF EXISTS webhook_token;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
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
            ],
        ),
        migrations.RunPython(add_column_and_populate, reverse_migration),
    ]
