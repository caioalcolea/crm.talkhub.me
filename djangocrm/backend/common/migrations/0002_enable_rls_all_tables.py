"""
Enable Row-Level Security on ALL org-scoped tables.

Single consolidated migration replacing all previous scattered RLS migrations.
This runs AFTER all app tables are created (depends on final migration of each app).

Tables list sourced from: common/rls/__init__.py -> ORG_SCOPED_TABLES
"""

from django.db import migrations

from common.rls import ORG_SCOPED_TABLES, get_enable_policy_sql, get_disable_policy_sql


def enable_rls(apps, schema_editor):
    """Enable RLS on all org-scoped tables."""
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    enabled = []
    skipped = []

    for table in ORG_SCOPED_TABLES:
        # Check if table exists before enabling RLS
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        exists = cursor.fetchone()[0]
        if exists:
            cursor.execute(get_enable_policy_sql(table))
            enabled.append(table)
        else:
            skipped.append(table)

    if skipped:
        print(f"\n  RLS: Enabled on {len(enabled)} tables, skipped {len(skipped)} (not found): {skipped}")
    else:
        print(f"\n  RLS: Enabled on all {len(enabled)} tables")


def disable_rls(apps, schema_editor):
    """Disable RLS on all org-scoped tables (reverse operation)."""
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in ORG_SCOPED_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        # Depends on the LAST migration of EVERY app to ensure all tables exist
        ("common", "0001_initial"),
        ("accounts", "0002_initial"),
        ("contacts", "0001_initial"),
        ("leads", "0001_initial"),
        ("cases", "0002_initial"),
        ("tasks", "0001_initial"),
        ("opportunity", "0001_initial"),
        ("invoices", "0002_initial"),
        ("orders", "0001_initial"),
        ("financeiro", "0002_initial"),
        ("integrations", "0001_initial"),
        ("talkhub_omni", "0001_initial"),
        ("crm_channels", "0002_initial"),
        ("conversations", "0001_initial"),
        ("automations", "0002_initial"),
        ("campaigns", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
