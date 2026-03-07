"""
Bug Condition Exploration Tests — Multi-Tenant Structure

These tests encode the EXPECTED behavior for the multi-tenant fix.
They are designed to FAIL on unfixed code, confirming the bug exists.

Bug conditions verified:
1. 10 tables missing from ORG_SCOPED_TABLES (no RLS protection)
2. 30+ models without OrgScopedManager (no .for_org()/.for_request())
3. save() without org_id does NOT raise ValidationError on affected models

After the fix is applied, these tests should PASS.

Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from common.base import OrgScopedManager
from common.rls import ORG_SCOPED_TABLES


# ── Tables that MUST be in ORG_SCOPED_TABLES but are currently missing ──

MISSING_RLS_TABLES = [
    "profile",
    "lead_pipeline",
    "lead_stage",
    "case_pipeline",
    "case_stage",
    "task_pipeline",
    "task_stage",
    "sales_goal",
    "stage_aging_config",
    "opportunity_line_item",
]

# ── Models that have org FK but inherit BaseModel (not BaseOrgModel) ──
# These should have OrgScopedManager but currently don't.

def _get_affected_models():
    """
    Lazily import all affected models.
    These are models with an org FK that inherit from BaseModel
    (not BaseOrgModel) and thus lack OrgScopedManager.
    """
    from common.models import (
        Address, Tags, Profile, Comment, CommentFiles,
        Attachments, Document, APISettings, Activity, Teams,
    )
    from leads.models import Lead, LeadPipeline, LeadStage
    from contacts.models import Contact
    from accounts.models import Account, AccountEmail, AccountEmailLog
    from opportunity.models import (
        Opportunity, OpportunityLineItem, StageAgingConfig,
        SalesGoal, GoalBreakdown,
    )
    from cases.models import Case, Solution, CasePipeline, CaseStage
    from tasks.models import (
        Task, Board, BoardMember, BoardColumn, BoardTask,
        TaskPipeline, TaskStage,
    )
    from invoices.models import (
        Invoice, InvoiceTemplate, Product, InvoiceLineItem, Payment,
        Estimate, EstimateLineItem, RecurringInvoice,
        RecurringInvoiceLineItem, InvoiceHistory,
    )
    from talkhub_omni.models import (
        TalkHubConnection, TalkHubSyncJob, TalkHubFieldMapping,
        TalkHubOmniChannel, TalkHubSyncConfig, TalkHubTeamMember,
        TalkHubTicketListMapping, OmniStatisticsSnapshot,
    )

    return [
        # common
        Address, Tags, Profile, Comment, CommentFiles,
        Attachments, Document, APISettings, Activity, Teams,
        # leads
        Lead, LeadPipeline, LeadStage,
        # contacts
        Contact,
        # accounts
        Account, AccountEmail, AccountEmailLog,
        # opportunity
        Opportunity, OpportunityLineItem, StageAgingConfig,
        SalesGoal, GoalBreakdown,
        # cases
        Case, Solution, CasePipeline, CaseStage,
        # tasks
        Task, Board, BoardMember, BoardColumn, BoardTask,
        TaskPipeline, TaskStage,
        # invoices
        Invoice, InvoiceTemplate, Product, InvoiceLineItem, Payment,
        Estimate, EstimateLineItem, RecurringInvoice,
        RecurringInvoiceLineItem, InvoiceHistory,
        # talkhub_omni
        TalkHubConnection, TalkHubSyncJob, TalkHubFieldMapping,
        TalkHubOmniChannel, TalkHubSyncConfig, TalkHubTeamMember,
        TalkHubTicketListMapping, OmniStatisticsSnapshot,
    ]


# Build the list at module level for hypothesis strategies
AFFECTED_MODELS = _get_affected_models()


# ═══════════════════════════════════════════════════════════════════════
# Test 1: Missing RLS tables
# ═══════════════════════════════════════════════════════════════════════

class TestMissingRLSTables:
    """
    Verify that the 10 missing tables ARE present in ORG_SCOPED_TABLES.
    On unfixed code, these assertions FAIL — confirming the bug.

    **Validates: Requirements 1.1**
    """

    @given(table=st.sampled_from(MISSING_RLS_TABLES))
    @settings(max_examples=len(MISSING_RLS_TABLES))
    def test_missing_tables_should_be_in_org_scoped_tables(self, table):
        """
        Property: For any table in MISSING_RLS_TABLES, it MUST be present
        in ORG_SCOPED_TABLES for RLS protection.

        **Validates: Requirements 1.1**
        """
        assert table in ORG_SCOPED_TABLES, (
            f"Table '{table}' has org_id column but is NOT in ORG_SCOPED_TABLES. "
            f"PostgreSQL RLS will NOT filter this table by organization, "
            f"allowing cross-tenant data leakage."
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 2: Models without OrgScopedManager
# ═══════════════════════════════════════════════════════════════════════

class TestModelsWithoutOrgScopedManager:
    """
    Verify that all affected models have OrgScopedManager as their
    default `objects` manager.
    On unfixed code, these assertions FAIL — confirming the bug.

    **Validates: Requirements 1.2**
    """

    @given(model=st.sampled_from(AFFECTED_MODELS))
    @settings(max_examples=len(AFFECTED_MODELS))
    def test_affected_models_should_have_org_scoped_manager(self, model):
        """
        Property: For any model with an org FK that is org-scoped,
        model.objects MUST be an instance of OrgScopedManager.

        **Validates: Requirements 1.2**
        """
        assert isinstance(model.objects, OrgScopedManager), (
            f"Model '{model.__name__}' has org FK but its `objects` manager "
            f"is {type(model.objects).__name__}, not OrgScopedManager. "
            f"This means .for_org() and .for_request() are not available, "
            f"risking cross-tenant data access."
        )


# ═══════════════════════════════════════════════════════════════════════
# Test 3: save() without org_id validation
# ═══════════════════════════════════════════════════════════════════════

class TestSaveWithoutOrgValidation:
    """
    Verify that affected models validate org_id on save().
    On unfixed code, models do NOT validate — confirming the bug.

    We check this by inspecting whether the model's save() method
    or its MRO includes org_id validation logic. We do NOT actually
    save to the database.

    **Validates: Requirements 1.3**
    """

    @given(model=st.sampled_from(AFFECTED_MODELS))
    @settings(max_examples=len(AFFECTED_MODELS))
    def test_affected_models_should_validate_org_on_save(self, model):
        """
        Property: For any org-scoped model, the save() chain MUST include
        org_id validation (via OrgScopedMixin or equivalent).

        We verify this by checking that OrgScopedManager is the default
        manager — which implies OrgScopedMixin is in the MRO, which
        provides the save() validation.

        **Validates: Requirements 1.3**
        """
        # If the model has OrgScopedManager, it means OrgScopedMixin
        # (or BaseOrgModel) is in the MRO, providing save() validation.
        # On unfixed code, this will be False for all affected models.
        has_org_scoped_manager = isinstance(model.objects, OrgScopedManager)

        assert has_org_scoped_manager, (
            f"Model '{model.__name__}' does not have OrgScopedManager, "
            f"which means its save() does NOT validate org_id presence. "
            f"Saving with org_id=None will succeed silently, creating "
            f"orphan records without organization."
        )
