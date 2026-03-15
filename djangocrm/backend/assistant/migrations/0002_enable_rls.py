"""
Enable Row-Level Security on all assistant tables.
"""

from django.db import migrations

from common.rls import get_enable_policy_sql, get_disable_policy_sql

ASSISTANT_TABLES = [
    "assistant_reminder_policy",
    "assistant_scheduled_job",
    "assistant_channel_dispatch",
    "assistant_task_link",
    "assistant_autopilot_template",
]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in ASSISTANT_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))

    print(f"\n  RLS: Enabled on {len(ASSISTANT_TABLES)} assistant tables")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in ASSISTANT_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
