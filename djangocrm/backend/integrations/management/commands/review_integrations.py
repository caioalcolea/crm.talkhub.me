"""
Management command: review_integrations

Executa o agente de revisão de integração para uma organização.

Uso:
    python manage.py review_integrations --org <org_id>
    python manage.py review_integrations --org <org_id> --fix
    python manage.py review_integrations --org <org_id> --json
    python manage.py review_integrations --all
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from common.models import Org
from integrations.review_agent import IntegrationReviewAgent


class Command(BaseCommand):
    help = "Executar revisão de integridade do sistema integrativo"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--org", type=str, help="UUID da organização")
        group.add_argument("--all", action="store_true", help="Revisar todas as orgs ativas")
        parser.add_argument("--fix", action="store_true", help="Aplicar correções automáticas")
        parser.add_argument("--json", action="store_true", help="Output em JSON")
        parser.add_argument(
            "--severity", type=str, default="all",
            choices=["all", "critical", "warning", "info"],
            help="Filtrar por severidade",
        )

    def handle(self, *args, **options):
        if options["all"]:
            orgs = Org.objects.filter(is_active=True)
        else:
            try:
                orgs = [Org.objects.get(id=options["org"])]
            except Org.DoesNotExist:
                raise CommandError(f"Org não encontrada: {options['org']}")

        all_reports = []

        for org in orgs:
            self._set_rls_context(org)
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Revisando: {org.name} ({org.id})")
            self.stdout.write(f"{'='*60}")

            agent = IntegrationReviewAgent(org, auto_fix=options["fix"])
            report = agent.run_full_review()
            all_reports.append(report)

            if options["json"]:
                continue

            self._print_report(report, options["severity"])

        if options["json"]:
            self.stdout.write(json.dumps(
                [r.to_dict() for r in all_reports], indent=2, default=str
            ))

    def _print_report(self, report, severity_filter):
        """Imprimir relatório formatado no terminal."""
        stats = report.stats
        self.stdout.write(f"\n📊 Estatísticas:")
        self.stdout.write(f"  Contacts: {stats.get('contacts_total', 0)} total, "
                         f"{stats.get('contacts_with_account', 0)} com account, "
                         f"{stats.get('contacts_with_email', 0)} com email, "
                         f"{stats.get('contacts_with_talkhub', 0)} com TalkHub")
        self.stdout.write(f"  Accounts: {stats.get('accounts_total', 0)}")
        self.stdout.write(f"  Leads: {stats.get('leads_total', 0)} total, "
                         f"{stats.get('leads_active', 0)} ativos")
        self.stdout.write(f"  Conversas: {stats.get('conversations_total', 0)} total, "
                         f"{stats.get('conversations_open', 0)} abertas")
        self.stdout.write(f"  Integrações ativas: {stats.get('integrations_active', 0)}")

        # Issues
        issues = report.issues
        if severity_filter != "all":
            issues = [i for i in issues if i.severity == severity_filter]

        if not issues:
            self.stdout.write(self.style.SUCCESS("\n✅ Nenhum problema encontrado!"))
            return

        self.stdout.write(f"\n⚠️  Problemas encontrados: {len(issues)}")
        self.stdout.write(f"  🔴 Critical: {report.critical_count}")
        self.stdout.write(f"  🟡 Warning: {report.warning_count}")
        self.stdout.write(f"  🔵 Info: {report.info_count}")
        self.stdout.write(f"  🔧 Auto-fixable: {report.fixable_count}")

        severity_icons = {"critical": "🔴", "warning": "🟡", "info": "🔵"}

        for issue in issues:
            icon = severity_icons.get(issue.severity, "❓")
            fix_tag = " [FIXABLE]" if issue.auto_fixable else ""
            self.stdout.write(
                f"\n  {icon} [{issue.category}] {issue.entity_type}"
                f"{f' ({issue.entity_id[:8]}...)' if issue.entity_id else ''}"
                f"{fix_tag}"
            )
            self.stdout.write(f"     {issue.message}")

        # Fixes applied
        if report.fixes_applied:
            self.stdout.write(self.style.SUCCESS(
                f"\n🔧 Correções aplicadas: {len(report.fixes_applied)}"
            ))
            for fix in report.fixes_applied:
                self.stdout.write(f"  ✅ {fix}")

    @staticmethod
    def _set_rls_context(org):
        """Definir contexto RLS para a org."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org', %s, false)",
                [str(org.id)],
            )
