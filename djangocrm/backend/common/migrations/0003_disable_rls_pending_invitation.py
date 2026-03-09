"""
Disable RLS on tables that must be queryable without org context.

- pending_invitation: Queried by token on public accept flow (no auth/org context).
- profile: Queried by GetProfileAndOrg middleware BEFORE RLS context is set.
  Also queried cross-org (user sees all their orgs via GET /api/org/).
  Application-level security (JWT claims + middleware) handles access control.
- security_audit_log: Has nullable org (platform-level events have org=None).
  RLS makes NULL org_id rows permanently inaccessible.
"""

from django.db import migrations

from common.rls import get_disable_policy_sql, get_enable_policy_sql

# Tables that should NOT have RLS
TABLES_TO_EXCLUDE = ["pending_invitation", "profile", "security_audit_log"]


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    cursor = schema_editor.connection.cursor()
    for table in TABLES_TO_EXCLUDE:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))
            print(f"\n  RLS: Disabled on {table}")


def enable_rls(apps, schema_editor):
    """Reverse: re-enable RLS."""
    if schema_editor.connection.vendor != "postgresql":
        return
    cursor = schema_editor.connection.cursor()
    for table in TABLES_TO_EXCLUDE:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table],
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0002_enable_rls_all_tables"),
    ]

    operations = [
        migrations.RunPython(disable_rls, enable_rls),
    ]
