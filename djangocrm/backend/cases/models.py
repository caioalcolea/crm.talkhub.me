from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from accounts.models import Account
from common.base import AssignableMixin, BaseModel, OrgScopedMixin
from common.models import Org, Profile, Tags, Teams
from common.utils import CASE_TYPE, PRIORITY_CHOICE, STATUS_CHOICE
from contacts.models import Contact


# Cleanup notes:
# - Removed 'created_on_arrow' property from Case and Solution (frontend computes its own timestamps)
# - Fixed case_type default from "" to None (empty string is bad default for nullable field)


class Case(AssignableMixin, OrgScopedMixin, BaseModel):
    name = models.CharField(pgettext_lazy("Name of the case", "Name"), max_length=64)
    status = models.CharField(choices=STATUS_CHOICE, max_length=64)
    priority = models.CharField(choices=PRIORITY_CHOICE, max_length=64)
    case_type = models.CharField(
        choices=CASE_TYPE, max_length=255, blank=True, null=True, default=None
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="accounts_cases",
    )
    contacts = models.ManyToManyField(Contact, related_name="case_contacts")
    closed_on = models.DateField(blank=True, null=True)
    due_date = models.DateField(_("due date"), blank=True, null=True)
    due_time = models.TimeField(_("due time"), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ManyToManyField(Profile, related_name="case_assigned_users")
    is_active = models.BooleanField(default=True)
    teams = models.ManyToManyField(Teams, related_name="cases_teams")
    tags = models.ManyToManyField(Tags, related_name="case_tags", blank=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="cases")

    # SLA Tracking Fields
    first_response_at = models.DateTimeField(
        _("First Response At"), blank=True, null=True
    )
    resolved_at = models.DateTimeField(_("Resolved At"), blank=True, null=True)
    sla_first_response_hours = models.PositiveIntegerField(
        _("First Response SLA (hours)"),
        default=4,
        help_text="Target hours for first response",
    )
    sla_resolution_hours = models.PositiveIntegerField(
        _("Resolution SLA (hours)"),
        default=24,
        help_text="Target hours for resolution",
    )

    # Kanban/Pipeline support
    stage = models.ForeignKey(
        "CaseStage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        help_text="Current pipeline stage (null = use status-based kanban)",
    )
    kanban_order = models.DecimalField(
        _("Kanban Order"),
        max_digits=15,
        decimal_places=6,
        default=0,
        help_text="Order within the kanban column for drag-drop positioning",
    )

    # TalkHub Omni correlation
    omni_ticket_item_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="TalkHub Omni ticket item ID",
    )
    omni_ticket_list_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="TalkHub Omni ticket list ID",
    )
    sla_priority = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"), ("medium", "Medium"),
            ("high", "High"), ("urgent", "Urgent"),
        ],
        default="medium",
        help_text="SLA priority level — affects response/resolution targets",
    )
    escalation_level = models.PositiveSmallIntegerField(
        default=0,
        help_text="Current escalation level (0=none, 1=L1, 2=L2, 3=L3)",
    )
    escalated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the case was last escalated",
    )

    class Meta:
        verbose_name = "Case"
        verbose_name_plural = "Cases"
        db_table = "case"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["due_date", "due_time"]),
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["stage", "kanban_order"]),
            models.Index(fields=["status", "kanban_order"]),
        ]

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        """Validate case data."""
        super().clean()
        errors = {}

        # Closed date required when status is Closed
        if self.status == "Closed" and not self.closed_on:
            errors["closed_on"] = _("Closed date is required when closing a case")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Auto-set SLA values based on priority for new cases."""
        from .workflow import DEFAULT_FIRST_RESPONSE_SLA, DEFAULT_RESOLUTION_SLA

        # Validate stage belongs to correct org
        if self.stage_id and self.stage.org_id != self.org_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Case stage must belong to the same organization")

        # Set default SLA based on priority for new cases
        if not self.pk:
            if self.sla_first_response_hours == 4:  # Default value
                self.sla_first_response_hours = DEFAULT_FIRST_RESPONSE_SLA.get(
                    self.priority, 4
                )
            if self.sla_resolution_hours == 24:  # Default value
                self.sla_resolution_hours = DEFAULT_RESOLUTION_SLA.get(
                    self.priority, 24
                )

        super().save(*args, **kwargs)

    @property
    def is_sla_first_response_breached(self) -> bool:
        """Check if first response SLA has been breached."""
        if self.first_response_at:
            return False
        if not self.created_at:
            return False
        deadline = self.created_at + timedelta(hours=self.sla_first_response_hours)
        return timezone.now() > deadline

    @property
    def is_sla_resolution_breached(self) -> bool:
        """Check if resolution SLA has been breached."""
        if self.resolved_at:
            return False
        if not self.created_at:
            return False
        deadline = self.created_at + timedelta(hours=self.sla_resolution_hours)
        return timezone.now() > deadline

    @property
    def first_response_sla_deadline(self):
        """Return the deadline for first response."""
        if self.created_at:
            return self.created_at + timedelta(hours=self.sla_first_response_hours)
        return None

    @property
    def resolution_sla_deadline(self):
        """Return the deadline for resolution."""
        if self.created_at:
            return self.created_at + timedelta(hours=self.sla_resolution_hours)
        return None

    @property
    def is_overdue(self) -> bool:
        """Check if case is overdue (past due date/time and not closed)."""
        if self.status in ("Closed", "Rejected", "Duplicate"):
            return False
        if not self.due_date:
            return False
        now = timezone.now()
        today = now.date()
        if today > self.due_date:
            return True
        if today == self.due_date and self.due_time:
            return timezone.localtime(now).time() > self.due_time
        return False

    @property
    def days_until_due(self) -> int | None:
        """Return days until due (negative if overdue). None if no due date."""
        if not self.due_date:
            return None
        return (self.due_date - timezone.now().date()).days

    @property
    def subtask_progress(self) -> str:
        """Return subtask completion progress as 'completed/total'."""
        total = self.subtasks.count()
        if total == 0:
            return ""
        completed = self.subtasks.filter(is_completed=True).count()
        return f"{completed}/{total}"


class Solution(OrgScopedMixin, BaseModel):
    """
    Knowledge Base Solution

    Solutions are reusable answers/guides that can be linked to cases.
    They form a knowledge base for common issues and their resolutions.
    """

    title = models.CharField(max_length=255)
    description = models.TextField()

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("reviewed", "Reviewed"),
        ("approved", "Approved"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_published = models.BooleanField(default=False)

    # Organization relation
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="solutions")

    # Cases that use this solution
    cases = models.ManyToManyField(Case, related_name="solutions", blank=True)

    class Meta:
        verbose_name = "Solution"
        verbose_name_plural = "Solutions"
        db_table = "solution"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["org"]),
        ]

    def __str__(self):
        return self.title

    def publish(self):
        """Publish the solution (must be approved first)"""
        if self.status == "approved":
            self.is_published = True
            self.save()

    def unpublish(self):
        """Unpublish the solution"""
        self.is_published = False
        self.save()


class CasePipeline(OrgScopedMixin, BaseModel):
    """
    Custom pipeline for organizing cases into stages (Kanban columns).
    Each organization can have multiple pipelines (e.g., Support, Engineering, Billing).
    """

    name = models.CharField(_("Pipeline Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="case_pipelines"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="If true, new cases without explicit pipeline go here",
    )
    is_active = models.BooleanField(default=True)
    sla_priority_multipliers = models.JSONField(
        default=dict, blank=True,
        help_text='SLA multipliers by priority, e.g. {"urgent": 0.5, "high": 0.75, "medium": 1.0, "low": 1.5}',
    )
    auto_escalate = models.BooleanField(
        default=False,
        help_text="Auto-escalate cases when SLA is breached",
    )
    visible_to_teams = models.ManyToManyField(
        Teams, blank=True, related_name="visible_case_pipelines",
        help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
    )
    visible_to_users = models.ManyToManyField(
        Profile, blank=True, related_name="visible_case_pipelines",
        help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
    )

    class Meta:
        verbose_name = "Case Pipeline"
        verbose_name_plural = "Case Pipelines"
        db_table = "case_pipeline"
        ordering = ("-is_default", "name")
        indexes = [
            models.Index(fields=["org", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["org"],
                condition=models.Q(is_default=True),
                name="unique_default_case_pipeline_per_org",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.org.name})"


class CaseStage(OrgScopedMixin, BaseModel):
    """
    Stage within a Case Pipeline (Kanban column).
    """

    STAGE_TYPE_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
    ]

    pipeline = models.ForeignKey(
        CasePipeline, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(_("Stage Name"), max_length=100)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default="#6B7280")  # Hex color

    # Business logic fields
    stage_type = models.CharField(
        max_length=20, choices=STAGE_TYPE_CHOICES, default="open"
    )
    maps_to_status = models.CharField(
        _("Maps to Status"),
        max_length=64,
        blank=True,
        null=True,
        choices=STATUS_CHOICE,
        help_text="When case enters this stage, also update Case.status",
    )

    # Kanban features
    wip_limit = models.PositiveIntegerField(
        _("WIP Limit"),
        null=True,
        blank=True,
        help_text="Maximum cases allowed in this stage (null = unlimited)",
    )

    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="case_stages")

    class Meta:
        verbose_name = "Case Stage"
        verbose_name_plural = "Case Stages"
        db_table = "case_stage"
        ordering = ("order",)
        unique_together = ("pipeline", "name")
        indexes = [
            models.Index(fields=["org", "order"]),
            models.Index(fields=["pipeline", "order"]),
        ]

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.org_id and self.pipeline_id:
            self.org_id = self.pipeline.org_id
        super().save(*args, **kwargs)
