"""
Preservation Tests — Multi-Tenant Structure Fix

These tests capture BASELINE behavior that MUST be preserved after the fix.
They should PASS on the current (unfixed) code and continue to PASS after
the fix is applied.

Observation-first methodology:
1. Observe current behavior of models that already work correctly
2. Encode that behavior as tests
3. Ensure the fix does not break any of these behaviors

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

import pytest
from django.db import models
from hypothesis import given, settings
from hypothesis import strategies as st

from common.base import AssignableMixin, BaseOrgModel, OrgScopedManager
from common.rls import ORG_SCOPED_TABLES


# ═══════════════════════════════════════════════════════════════════════
# Data: Models that already use BaseOrgModel (should remain unchanged)
# ═══════════════════════════════════════════════════════════════════════

def _get_baseorgmodel_models():
    """Lazily import models that already inherit from BaseOrgModel."""
    from orders.models import Order, OrderLineItem
    from financeiro.models import (
        PlanoDeContasGrupo, PlanoDeContas, FormaPagamento,
        Lancamento, Parcela, PaymentTransaction,
    )
    from integrations.models import (
        OrgFeatureFlag, IntegrationConnection, SyncJob,
        IntegrationLog, WebhookLog, FieldMapping, ConflictLog,
    )
    from channels.models import ChannelConfig
    from conversations.models import Conversation, Message

    return [
        Order, OrderLineItem,
        PlanoDeContasGrupo, PlanoDeContas, FormaPagamento,
        Lancamento, Parcela, PaymentTransaction,
        OrgFeatureFlag, IntegrationConnection, SyncJob,
        IntegrationLog, WebhookLog, FieldMapping, ConflictLog,
        ChannelConfig,
        Conversation, Message,
    ]


BASEORGMODEL_MODELS = _get_baseorgmodel_models()


# ═══════════════════════════════════════════════════════════════════════
# Data: Models with custom related_name on org FK
# ═══════════════════════════════════════════════════════════════════════

def _get_models_with_related_names():
    """
    Models that have custom related_name on their org FK.
    Returns list of (model_class, expected_related_name) tuples.
    """
    from leads.models import Lead
    from contacts.models import Contact
    from accounts.models import Account
    from cases.models import Case
    from tasks.models import Task
    from opportunity.models import Opportunity
    from invoices.models import Invoice, Estimate, RecurringInvoice

    return [
        (Lead, "leads"),
        (Contact, "contacts"),
        (Account, "accounts"),
        (Case, "cases"),
        (Task, "tasks"),
        (Opportunity, "opportunities"),
        (Invoice, "invoices"),
        (Estimate, "estimates"),
        (RecurringInvoice, "recurring_invoices"),
    ]


MODELS_WITH_RELATED_NAMES = _get_models_with_related_names()


# ═══════════════════════════════════════════════════════════════════════
# Data: Tables already in ORG_SCOPED_TABLES
# ═══════════════════════════════════════════════════════════════════════

EXISTING_RLS_TABLES = [
    "lead",
    "accounts",
    "contacts",
    "opportunity",
    "case",
    "task",
    "invoice",
    "comment",
    "commentFiles",
    "attachments",
    "document",
    "teams",
    "activity",
    "tags",
    "address",
    "solution",
    "board",
    "board_column",
    "board_task",
    "board_member",
    "apiSettings",
    "account_email",
    "emailLogs",
    "invoice_history",
    "invoice_line_item",
    "invoice_template",
    "payment",
    "estimate",
    "estimate_line_item",
    "recurring_invoice",
    "recurring_invoice_line_item",
    "product",
    "orders",
    "order_line_item",
    "security_audit_log",
    "talkhub_connection",
    "talkhub_sync_job",
    "talkhub_field_mapping",
    "talkhub_omni_channel",
    "talkhub_sync_config",
    "talkhub_team_member",
    "talkhub_ticket_list_mapping",
    "omni_statistics_snapshot",
    "org_feature_flag",
    "integration_connection",
    "sync_job",
    "integration_log",
    "webhook_log",
    "field_mapping",
    "conflict_log",
    "channel_config",
    "conversation",
    "message",
    "financeiro_plano_grupo",
    "financeiro_plano_contas",
    "financeiro_forma_pagamento",
    "financeiro_lancamento",
    "financeiro_parcela",
    "pending_invitation",
    "automation",
    "automation_log",
    "goal_breakdown",
    "payment_transaction",
    "campaign",
    "campaign_audience",
    "campaign_recipient",
    "campaign_step",
]


# ═══════════════════════════════════════════════════════════════════════
# Data: Models using AssignableMixin
# ═══════════════════════════════════════════════════════════════════════

def _get_assignable_models():
    """Models that use AssignableMixin."""
    from leads.models import Lead
    from contacts.models import Contact
    from accounts.models import Account
    from opportunity.models import Opportunity
    from cases.models import Case
    from tasks.models import Task
    from invoices.models import Invoice, Estimate, RecurringInvoice

    return [
        Lead, Contact, Account, Opportunity,
        Case, Task, Invoice, Estimate, RecurringInvoice,
    ]


ASSIGNABLE_MODELS = _get_assignable_models()


# ═══════════════════════════════════════════════════════════════════════
# Data: Meta configurations to preserve
# ═══════════════════════════════════════════════════════════════════════

def _get_meta_configs():
    """
    Capture current Meta configurations for affected models.
    Returns list of (model_class, expected_db_table) tuples.
    """
    from leads.models import Lead, LeadPipeline, LeadStage
    from contacts.models import Contact
    from accounts.models import Account, AccountEmail, AccountEmailLog
    from opportunity.models import Opportunity, OpportunityLineItem, StageAgingConfig, SalesGoal, GoalBreakdown
    from cases.models import Case, Solution, CasePipeline, CaseStage
    from tasks.models import Task, Board, BoardMember, BoardColumn, BoardTask, TaskPipeline, TaskStage
    from invoices.models import (
        Invoice, InvoiceTemplate, Product, InvoiceLineItem, Payment,
        Estimate, EstimateLineItem, RecurringInvoice, RecurringInvoiceLineItem,
        InvoiceHistory,
    )
    from common.models import (
        Address, Tags, Profile, Comment, CommentFiles,
        Attachments, Document, APISettings, Activity, Teams,
    )
    from talkhub_omni.models import TalkHubConnection

    return [
        (Lead, "lead"),
        (LeadPipeline, "lead_pipeline"),
        (LeadStage, "lead_stage"),
        (Contact, "contacts"),
        (Account, "accounts"),
        (AccountEmail, "account_email"),
        (AccountEmailLog, "emailLogs"),
        (Opportunity, "opportunity"),
        (OpportunityLineItem, "opportunity_line_item"),
        (StageAgingConfig, "stage_aging_config"),
        (SalesGoal, "sales_goal"),
        (GoalBreakdown, "goal_breakdown"),
        (Case, "case"),
        (Solution, "solution"),
        (CasePipeline, "case_pipeline"),
        (CaseStage, "case_stage"),
        (Task, "task"),
        (Board, "board"),
        (BoardMember, "board_member"),
        (BoardColumn, "board_column"),
        (BoardTask, "board_task"),
        (TaskPipeline, "task_pipeline"),
        (TaskStage, "task_stage"),
        (Invoice, "invoice"),
        (InvoiceTemplate, "invoice_template"),
        (Product, "product"),
        (InvoiceLineItem, "invoice_line_item"),
        (Payment, "payment"),
        (Estimate, "estimate"),
        (EstimateLineItem, "estimate_line_item"),
        (RecurringInvoice, "recurring_invoice"),
        (RecurringInvoiceLineItem, "recurring_invoice_line_item"),
        (InvoiceHistory, "invoice_history"),
        (Address, "address"),
        (Tags, "tags"),
        (Profile, "profile"),
        (Comment, "comment"),
        (CommentFiles, "commentFiles"),
        (Attachments, "attachments"),
        (Document, "document"),
        (APISettings, "apiSettings"),
        (Activity, "activity"),
        (Teams, "teams"),
        (TalkHubConnection, "talkhub_connection"),
    ]


META_CONFIGS = _get_meta_configs()


# ═══════════════════════════════════════════════════════════════════════
# Test 1: BaseOrgModel Preservation
# ═══════════════════════════════════════════════════════════════════════

class TestBaseOrgModelPreservation:
    """
    Models that already use BaseOrgModel (orders, financeiro, integrations,
    channels, conversations) must continue to have OrgScopedManager and
    org_id validation in save().

    **Validates: Requirements 3.5**
    """

    @given(model=st.sampled_from(BASEORGMODEL_MODELS))
    @settings(max_examples=len(BASEORGMODEL_MODELS))
    def test_baseorgmodel_has_org_scoped_manager(self, model):
        """
        Property: For any model inheriting BaseOrgModel, objects MUST be
        an instance of OrgScopedManager.

        **Validates: Requirements 3.5**
        """
        assert isinstance(model.objects, OrgScopedManager), (
            f"Model '{model.__name__}' inherits BaseOrgModel but its `objects` "
            f"manager is {type(model.objects).__name__}, not OrgScopedManager."
        )

    @given(model=st.sampled_from(BASEORGMODEL_MODELS))
    @settings(max_examples=len(BASEORGMODEL_MODELS))
    def test_baseorgmodel_inherits_from_baseorgmodel(self, model):
        """
        Property: For any model in BASEORGMODEL_MODELS, it MUST be a
        subclass of BaseOrgModel.

        **Validates: Requirements 3.5**
        """
        assert issubclass(model, BaseOrgModel), (
            f"Model '{model.__name__}' is expected to inherit from BaseOrgModel "
            f"but does not. MRO: {[c.__name__ for c in model.__mro__]}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 2: Related Name Preservation
# ═══════════════════════════════════════════════════════════════════════

class TestRelatedNamePreservation:
    """
    Custom related_name values on org FK must be preserved exactly.
    These are used in reverse queries like org.leads.all().

    **Validates: Requirements 3.3**
    """

    @given(data=st.sampled_from(MODELS_WITH_RELATED_NAMES))
    @settings(max_examples=len(MODELS_WITH_RELATED_NAMES))
    def test_org_fk_related_name_preserved(self, data):
        """
        Property: For any model with a custom related_name on org FK,
        the related_name MUST match the expected value.

        **Validates: Requirements 3.3**
        """
        model, expected_related_name = data
        org_field = model._meta.get_field("org")
        actual_related_name = org_field.remote_field.related_name

        assert actual_related_name == expected_related_name, (
            f"Model '{model.__name__}' org FK related_name is "
            f"'{actual_related_name}', expected '{expected_related_name}'. "
            f"Changing this would break reverse queries like "
            f"org.{expected_related_name}.all()."
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 3: Existing RLS Tables Preservation
# ═══════════════════════════════════════════════════════════════════════

class TestExistingRLSTablesPreservation:
    """
    Tables already in ORG_SCOPED_TABLES must remain present after the fix.

    **Validates: Requirements 3.5**
    """

    @given(table=st.sampled_from(EXISTING_RLS_TABLES))
    @settings(max_examples=len(EXISTING_RLS_TABLES))
    def test_existing_rls_tables_remain_in_org_scoped_tables(self, table):
        """
        Property: For any table already in ORG_SCOPED_TABLES, it MUST
        continue to be present after the fix.

        **Validates: Requirements 3.5**
        """
        assert table in ORG_SCOPED_TABLES, (
            f"Table '{table}' was previously in ORG_SCOPED_TABLES but is now "
            f"missing. This would disable RLS protection for this table."
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 4: AssignableMixin Preservation
# ═══════════════════════════════════════════════════════════════════════

class TestAssignableMixinPreservation:
    """
    Models using AssignableMixin must continue to have get_team_users
    and get_team_and_assigned_users properties.

    **Validates: Requirements 3.2**
    """

    @given(model=st.sampled_from(ASSIGNABLE_MODELS))
    @settings(max_examples=len(ASSIGNABLE_MODELS))
    def test_assignable_models_have_mixin(self, model):
        """
        Property: For any model using AssignableMixin, it MUST be a
        subclass of AssignableMixin.

        **Validates: Requirements 3.2**
        """
        assert issubclass(model, AssignableMixin), (
            f"Model '{model.__name__}' should use AssignableMixin but does not. "
            f"MRO: {[c.__name__ for c in model.__mro__]}"
        )

    @given(model=st.sampled_from(ASSIGNABLE_MODELS))
    @settings(max_examples=len(ASSIGNABLE_MODELS))
    def test_assignable_models_have_get_team_users(self, model):
        """
        Property: For any model using AssignableMixin, it MUST have
        the get_team_users property.

        **Validates: Requirements 3.2**
        """
        assert hasattr(model, "get_team_users"), (
            f"Model '{model.__name__}' is missing 'get_team_users' property "
            f"from AssignableMixin."
        )

    @given(model=st.sampled_from(ASSIGNABLE_MODELS))
    @settings(max_examples=len(ASSIGNABLE_MODELS))
    def test_assignable_models_have_get_team_and_assigned_users(self, model):
        """
        Property: For any model using AssignableMixin, it MUST have
        the get_team_and_assigned_users property.

        **Validates: Requirements 3.2**
        """
        assert hasattr(model, "get_team_and_assigned_users"), (
            f"Model '{model.__name__}' is missing 'get_team_and_assigned_users' "
            f"property from AssignableMixin."
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 5: TalkHubConnection OneToOne Preservation
# ═══════════════════════════════════════════════════════════════════════

class TestTalkHubConnectionPreservation:
    """
    TalkHubConnection.org must remain a OneToOneField with
    related_name="talkhub_connection".

    **Validates: Requirements 3.4**
    """

    def test_talkhub_connection_org_is_one_to_one(self):
        """TalkHubConnection.org MUST be a OneToOneField."""
        from talkhub_omni.models import TalkHubConnection

        org_field = TalkHubConnection._meta.get_field("org")
        assert isinstance(org_field, models.OneToOneField), (
            f"TalkHubConnection.org is {type(org_field).__name__}, "
            f"expected OneToOneField. Changing this would break the "
            f"one-to-one relationship between Org and TalkHubConnection."
        )

    def test_talkhub_connection_related_name(self):
        """TalkHubConnection.org related_name MUST be 'talkhub_connection'."""
        from talkhub_omni.models import TalkHubConnection

        org_field = TalkHubConnection._meta.get_field("org")
        assert org_field.remote_field.related_name == "talkhub_connection", (
            f"TalkHubConnection.org related_name is "
            f"'{org_field.remote_field.related_name}', expected 'talkhub_connection'."
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 6: Meta Preservation (db_table)
# ═══════════════════════════════════════════════════════════════════════

class TestMetaPreservation:
    """
    Existing db_table, unique_together, constraints, and indexes on
    affected models must be preserved.

    **Validates: Requirements 3.7**
    """

    @given(data=st.sampled_from(META_CONFIGS))
    @settings(max_examples=len(META_CONFIGS))
    def test_db_table_preserved(self, data):
        """
        Property: For any affected model, its Meta.db_table MUST match
        the expected value.

        **Validates: Requirements 3.7**
        """
        model, expected_db_table = data
        actual_db_table = model._meta.db_table

        assert actual_db_table == expected_db_table, (
            f"Model '{model.__name__}' db_table is '{actual_db_table}', "
            f"expected '{expected_db_table}'. Changing db_table would require "
            f"a destructive migration."
        )

    def test_tags_unique_together_preserved(self):
        """Tags model must preserve unique_together = ['slug', 'org']."""
        from common.models import Tags

        unique_together = Tags._meta.unique_together
        assert ("slug", "org") in unique_together, (
            f"Tags unique_together is {unique_together}, "
            f"expected to contain ('slug', 'org')."
        )

    def test_profile_unique_together_preserved(self):
        """Profile model must preserve unique_together constraints."""
        from common.models import Profile

        unique_together = Profile._meta.unique_together
        assert ("user", "org") in unique_together, (
            f"Profile unique_together is {unique_together}, "
            f"expected to contain ('user', 'org')."
        )

    def test_account_constraints_preserved(self):
        """Account model must preserve its constraints."""
        from accounts.models import Account

        constraint_names = [c.name for c in Account._meta.constraints]
        assert "unique_account_name_per_org" in constraint_names, (
            f"Account constraints {constraint_names} missing "
            f"'unique_account_name_per_org'."
        )
        assert "account_revenue_non_negative" in constraint_names, (
            f"Account constraints {constraint_names} missing "
            f"'account_revenue_non_negative'."
        )

    def test_lead_constraints_preserved(self):
        """Lead model must preserve its constraints."""
        from leads.models import Lead

        constraint_names = [c.name for c in Lead._meta.constraints]
        assert "unique_lead_email_per_org" in constraint_names
        assert "lead_probability_range" in constraint_names
        assert "lead_amount_non_negative" in constraint_names

    def test_contact_constraints_preserved(self):
        """Contact model must preserve its constraints."""
        from contacts.models import Contact

        constraint_names = [c.name for c in Contact._meta.constraints]
        assert "unique_contact_email_per_org" in constraint_names

    def test_opportunity_constraints_preserved(self):
        """Opportunity model must preserve its constraints."""
        from opportunity.models import Opportunity

        constraint_names = [c.name for c in Opportunity._meta.constraints]
        assert "opportunity_probability_range" in constraint_names
        assert "opportunity_amount_non_negative" in constraint_names
