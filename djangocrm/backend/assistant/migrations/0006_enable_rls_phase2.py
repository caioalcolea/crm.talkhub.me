"""
Enable Row-Level Security on notification and assistant_job_attempt tables.
"""

from django.db import migrations

from common.rls import get_enable_policy_sql, get_disable_policy_sql

PHASE2_TABLES = [
    "notification",
    "assistant_job_attempt",
]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in PHASE2_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))

    print(f"\n  RLS: Enabled on {len(PHASE2_TABLES)} phase 2 tables")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in PHASE2_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0005_notification_jobattempt"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
