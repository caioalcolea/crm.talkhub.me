"""
Enable Row-Level Security on opportunity_pipeline and opportunity_stage tables.
"""

from django.db import migrations

from common.rls import get_enable_policy_sql, get_disable_policy_sql

RLS_TABLES = [
    "opportunity_pipeline",
    "opportunity_stage",
]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in RLS_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))

    print(f"\n  RLS: Enabled on {', '.join(RLS_TABLES)}")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in RLS_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))

    print(f"\n  RLS: Disabled on {', '.join(RLS_TABLES)}")


class Migration(migrations.Migration):

    dependencies = [
        ("opportunity", "0002_opportunity_pipeline"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
