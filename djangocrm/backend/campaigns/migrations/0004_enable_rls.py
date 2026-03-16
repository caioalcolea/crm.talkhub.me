"""
Enable Row-Level Security on all campaigns tables.
"""

from django.db import migrations

from common.rls import get_enable_policy_sql, get_disable_policy_sql

CAMPAIGN_TABLES = [
    "campaign",
    "campaign_audience",
    "campaign_recipient",
    "campaign_step",
]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in CAMPAIGN_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))

    print(f"\n  RLS: Enabled on {len(CAMPAIGN_TABLES)} campaigns tables")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    cursor = schema_editor.connection.cursor()
    for table in CAMPAIGN_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0003_campaignrecipient_scheduled_job"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
