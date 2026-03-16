"""
Enable Row-Level Security on stock_movement table.
"""

from django.db import migrations

from common.rls import get_enable_policy_sql, get_disable_policy_sql

RLS_TABLES = [
    "stock_movement",
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

    print(f"\n  RLS: Enabled on stock_movement")


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

    print(f"\n  RLS: Disabled on stock_movement")


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0003_product_evolution_stock_movement"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
