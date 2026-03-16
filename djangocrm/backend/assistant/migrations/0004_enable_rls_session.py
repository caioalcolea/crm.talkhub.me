"""
Enable Row-Level Security on assistant_session and assistant_message tables.
"""

from django.db import migrations

from common.rls import get_enable_policy_sql, get_disable_policy_sql

SESSION_TABLES = [
    "assistant_session",
    "assistant_message",
]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in SESSION_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))

    print(f"\n  RLS: Enabled on {len(SESSION_TABLES)} session tables")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in SESSION_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0003_assistant_session"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
