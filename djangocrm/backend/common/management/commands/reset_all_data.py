"""
Management command to reset ALL business data across organizations.

Deletes everything except: Org, User, Profile, ChannelConfig, IntegrationConnection, Teams.
After clearing, optionally re-seeds default Centro de Custo and Formas de Pagamento.

Usage:
    python manage.py reset_all_data --all-orgs --confirm
    python manage.py reset_all_data --org-id UUID --confirm
    python manage.py reset_all_data --all-orgs --confirm --skip-seed
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from common.models import Org
from common.rls import get_set_context_sql


class Command(BaseCommand):
    help = "Reset ALL business data for organizations (financeiro, campaigns, assistant, CRM, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-id",
            type=str,
            help="UUID of specific organization to reset",
        )
        parser.add_argument(
            "--all-orgs",
            action="store_true",
            help="Reset all active organizations",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required flag to confirm destructive operation",
        )
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="Skip re-seeding defaults after reset",
        )

    def handle(self, *args, **options):
        org_id = options.get("org_id")
        all_orgs = options.get("all_orgs")
        confirm = options.get("confirm")
        skip_seed = options.get("skip_seed", False)

        if not org_id and not all_orgs:
            raise CommandError("Specify --org-id UUID or --all-orgs")

        if not confirm:
            raise CommandError(
                "This will DELETE ALL business data permanently. "
                "Pass --confirm to proceed."
            )

        if org_id:
            try:
                orgs = [Org.objects.get(id=org_id)]
            except Org.DoesNotExist:
                raise CommandError(f"Organization {org_id} not found")
        else:
            orgs = list(Org.objects.filter(is_active=True))

        self.stdout.write(
            self.style.WARNING(
                f"RESETTING ALL DATA for {len(orgs)} organization(s)..."
            )
        )

        for org in orgs:
            self.reset_org(org)

        if not skip_seed:
            self.stdout.write("\nRe-seeding defaults...")
            from common.management.commands.seed_org_defaults import seed_for_org

            for org in orgs:
                seed_for_org(org, force=True, stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS("\nReset complete!"))

    def reset_org(self, org):
        """Delete all business data for a single org in dependency order."""
        self.stdout.write(f"\n--- Resetting org: {org.name} ({org.id}) ---")

        # Set RLS context
        with connection.cursor() as cursor:
            cursor.execute(get_set_context_sql(), [str(org.id)])

        # 1. Assistant
        self._delete_model("assistant", "ChannelDispatch", org)
        self._delete_model("assistant", "TaskLink", org)
        self._delete_model("assistant", "ScheduledJob", org)
        self._delete_model("assistant", "ReminderPolicy", org)
        self._delete_model("assistant", "AutopilotTemplate", org)

        # 2. Campaigns
        self._delete_model("campaigns", "CampaignRecipient", org)
        self._delete_model("campaigns", "CampaignStep", org)
        self._delete_model("campaigns", "CampaignAudience", org)
        self._delete_model("campaigns", "Campaign", org)

        # 3. Automations
        self._delete_model("automations", "AutomationLog", org)
        self._delete_model("automations", "Automation", org)

        # 4. Financeiro
        self._delete_model("financeiro", "PaymentTransaction", org)
        self._delete_model("financeiro", "Parcela", org)
        self._delete_model("financeiro", "Lancamento", org)
        self._delete_model("financeiro", "FormaPagamento", org)
        self._delete_model("financeiro", "PlanoDeContas", org)
        self._delete_model("financeiro", "PlanoDeContasGrupo", org)

        # 5. Conversations
        self._delete_model("conversations", "Message", org)
        self._delete_model("conversations", "Conversation", org)

        # 6. Invoices (via seed helper pattern)
        self._delete_model("invoices", "InvoiceItem", org, fk_field="invoice__org")
        self._delete_model("invoices", "Payment", org, fk_field="invoice__org")
        self._delete_model("invoices", "Invoice", org)
        self._delete_model("invoices", "Estimate", org)
        self._delete_model("invoices", "Product", org)

        # 7. Tasks
        self._delete_model("tasks", "BoardTask", org)
        self._delete_model("tasks", "BoardColumn", org, fk_field="board__org")
        self._delete_model("tasks", "BoardMember", org, fk_field="board__org")
        self._delete_model("tasks", "Board", org)
        self._delete_model("tasks", "Task", org)
        self._delete_model("tasks", "TaskStage", org, fk_field="pipeline__org")
        self._delete_model("tasks", "TaskPipeline", org)

        # 8. Cases
        self._delete_model("cases", "Case", org)

        # 9. Opportunities
        self._delete_model("opportunity", "GoalBreakdown", org, fk_field="goal__org")
        self._delete_model("opportunity", "SalesGoal", org)
        self._delete_model("opportunity", "StageAgingConfig", org)
        self._delete_model("opportunity", "OpportunityLineItem", org, fk_field="opportunity__org")
        self._delete_model("opportunity", "Opportunity", org)

        # 10. Leads
        self._delete_model("leads", "Lead", org)

        # 11. Orders
        self._delete_model("orders", "OrderLineItem", org, fk_field="order__org")
        self._delete_model("orders", "Order", org)

        # 12. Contacts
        self._delete_model("contacts", "ContactEmail", org, fk_field="contact__org")
        self._delete_model("contacts", "ContactPhone", org, fk_field="contact__org")
        self._delete_model("contacts", "ContactAddress", org, fk_field="contact__org")
        self._delete_model("contacts", "Contact", org)

        # 13. Accounts
        self._delete_model("accounts", "Account", org)

        # 14. Tags & Activity
        self._delete_model("common", "Tags", org)
        self._delete_model("common", "Activity", org)

        self.stdout.write(self.style.SUCCESS(f"  Org {org.name}: all data cleared"))

    def _delete_model(self, app_label, model_name, org, fk_field=None):
        """Delete all instances of a model for an org."""
        from django.apps import apps

        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            self.stdout.write(f"  [skip] {app_label}.{model_name} not found")
            return

        try:
            if fk_field:
                # Model doesn't have direct org FK — use related field
                count, _ = Model.objects.filter(**{fk_field: org}).delete()
            elif hasattr(Model, "org"):
                count, _ = Model.objects.filter(org=org).delete()
            else:
                # Try org_id
                count, _ = Model.objects.filter(org_id=org.id).delete()

            if count > 0:
                self.stdout.write(f"  Deleted {count} {model_name}")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  [warn] {app_label}.{model_name}: {e}")
            )
