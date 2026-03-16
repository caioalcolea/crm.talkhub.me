from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.timesince import timesince
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from common.base import AssignableMixin, BaseModel, OrgScopedMixin
from common.models import Org, Profile, Tags, Teams
from common.utils import (
    CURRENCY_CODES,
    GOAL_TYPES,
    OPPORTUNITY_TYPES,
    PERIOD_TYPES,
    SOURCES,
    STAGES,
)
from contacts.models import Contact


# Amount source choices for Opportunity
AMOUNT_SOURCE_CHOICES = (
    ("MANUAL", "Manual"),
    ("CALCULATED", "Calculated from Products"),
)

# Discount type choices
DISCOUNT_TYPES = (
    ("PERCENTAGE", "Percentage (%)"),
    ("FIXED", "Fixed Amount"),
)


class Opportunity(AssignableMixin, OrgScopedMixin, BaseModel):
    """
    Opportunity model for CRM - Sales pipeline management
    Based on Twenty CRM and Salesforce patterns
    """

    # Core Opportunity Information
    name = models.CharField(_("Opportunity Name"), max_length=255)
    account = models.ForeignKey(
        Account,
        related_name="opportunities",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    stage = models.CharField(
        _("Stage"), max_length=64, choices=STAGES, default="PROSPECTING"
    )
    opportunity_type = models.CharField(
        _("Type"), max_length=64, choices=OPPORTUNITY_TYPES, blank=True, null=True
    )

    # Financial Information
    currency = models.CharField(
        _("Currency"), max_length=10, choices=CURRENCY_CODES, blank=True, null=True
    )
    amount = models.DecimalField(
        _("Amount"), decimal_places=2, max_digits=12, blank=True, null=True
    )
    amount_source = models.CharField(
        _("Amount Source"),
        max_length=20,
        choices=AMOUNT_SOURCE_CHOICES,
        default="MANUAL",
    )
    probability = models.IntegerField(
        _("Probability (%)"), default=0, blank=True, null=True
    )
    closed_on = models.DateField(_("Expected Close Date"), blank=True, null=True)

    # Source & Context
    lead_source = models.CharField(
        _("Lead Source"), max_length=255, choices=SOURCES, blank=True, null=True
    )

    # Relationships
    contacts = models.ManyToManyField(Contact, related_name="opportunity_contacts")
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
        help_text="Lead that originated this opportunity",
    )

    # Assignment
    assigned_to = models.ManyToManyField(
        Profile, related_name="opportunity_assigned_users"
    )
    teams = models.ManyToManyField(Teams, related_name="opportunity_teams")
    closed_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunity_closed_by",
    )

    # Tags
    tags = models.ManyToManyField(Tags, related_name="opportunity_tags", blank=True)

    # Notes
    description = models.TextField(_("Notes"), blank=True, null=True)

    # Deal Aging
    stage_changed_at = models.DateTimeField(
        _("Stage Changed At"), null=True, blank=True
    )

    # Pipeline/Kanban support
    pipeline_stage = models.ForeignKey(
        "OpportunityStage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
        help_text="Pipeline stage (null = use legacy stage CharField)",
    )
    kanban_order = models.DecimalField(
        _("Kanban Order"),
        max_digits=15,
        decimal_places=6,
        default=0,
        help_text="Order within the kanban column for drag-drop positioning",
    )

    # System Fields
    is_active = models.BooleanField(default=True)
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="opportunities",
    )

    class Meta:
        verbose_name = "Opportunity"
        verbose_name_plural = "Opportunities"
        db_table = "opportunity"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["stage"]),
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["pipeline_stage", "kanban_order"]),
            models.Index(fields=["stage", "kanban_order"]),
        ]
        constraints = [
            # Probability must be 0-100
            models.CheckConstraint(
                check=Q(probability__gte=0) & Q(probability__lte=100),
                name="opportunity_probability_range",
            ),
            # Amount must be non-negative
            models.CheckConstraint(
                check=Q(amount__gte=0) | Q(amount__isnull=True),
                name="opportunity_amount_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.name}"

    @property
    def created_on_arrow(self):
        return timesince(self.created_at) + " ago"

    def clean(self):
        """Validate opportunity data."""
        super().clean()
        errors = {}

        # Closed date required for closed stages
        if self.stage in ["CLOSED_WON", "CLOSED_LOST"] and not self.closed_on:
            errors["closed_on"] = _(
                "Close date is required when stage is Closed Won/Lost"
            )

        # Amount required for closed won
        if self.stage == "CLOSED_WON" and not self.amount:
            errors["amount"] = _("Amount is required for Closed Won opportunities")

        if errors:
            raise ValidationError(errors)

    def recalculate_amount(self):
        """
        Recalculate opportunity amount from line items.
        Only updates if amount_source is CALCULATED or if line items exist.
        Returns True if amount was updated, False otherwise.
        """
        line_items = self.line_items.all()
        if line_items.exists():
            total = line_items.aggregate(total=Sum("total"))["total"] or Decimal("0")
            self.amount = total
            self.amount_source = "CALCULATED"
            return True
        if self.amount_source == "CALCULATED":
            # No line items but was calculated - reset to manual
            self.amount_source = "MANUAL"
            self.amount = Decimal("0")
            return True
        return False

    @property
    def days_in_current_stage(self):
        """Number of days the deal has been in its current stage."""
        if not self.stage_changed_at:
            return 0
        delta = timezone.now() - self.stage_changed_at
        return delta.days

    def get_aging_status(self, aging_configs=None):
        """Return 'green', 'yellow', or 'red' based on deal aging.

        Args:
            aging_configs: Optional dict {stage: StageAgingConfig} to avoid DB queries.
                           Pass this when processing lists to prevent N+1.
        """
        from .workflow import CLOSED_STAGES, DEFAULT_STAGE_EXPECTED_DAYS, ROTTEN_MULTIPLIER

        if self.stage in CLOSED_STAGES:
            return "green"

        # Look up per-org config, fall back to defaults
        expected = DEFAULT_STAGE_EXPECTED_DAYS.get(self.stage)
        warning = None

        if aging_configs is not None:
            config = aging_configs.get(self.stage)
        else:
            config = StageAgingConfig.objects.filter(
                org=self.org, stage=self.stage
            ).first()

        if config:
            expected = config.expected_days
            warning = config.warning_days

        if expected is None:
            return "green"

        days = self.days_in_current_stage
        rotten_threshold = expected * ROTTEN_MULTIPLIER

        if days >= rotten_threshold:
            return "red"
        if warning and days >= warning:
            return "yellow"
        if days >= expected:
            return "yellow"
        return "green"

    @property
    def aging_status(self):
        """Return 'green', 'yellow', or 'red' based on deal aging."""
        return self.get_aging_status()

    def save(self, *args, **kwargs):
        """Auto-set probability and track stage changes."""
        # Validate pipeline_stage belongs to correct org
        if self.pipeline_stage_id and self.pipeline_stage.org_id != self.org_id:
            raise ValidationError(
                "Opportunity pipeline stage must belong to the same organization"
            )

        from .workflow import STAGE_PROBABILITIES

        # Auto-set probability based on stage (only if probability is default/0)
        if self.probability == 0 or self.probability is None:
            self.probability = STAGE_PROBABILITIES.get(self.stage, 0)

        # Track stage changes for deal aging
        if not self._state.adding:
            old_stage = (
                Opportunity.objects.filter(pk=self.pk)
                .values_list("stage", flat=True)
                .first()
            )
            if old_stage and old_stage != self.stage:
                self.stage_changed_at = timezone.now()
                # Ensure stage_changed_at is persisted when update_fields is used
                if kwargs.get("update_fields") is not None:
                    update_fields = set(kwargs["update_fields"])
                    update_fields.add("stage_changed_at")
                    kwargs["update_fields"] = list(update_fields)
        else:
            # New record
            if not self.stage_changed_at:
                self.stage_changed_at = timezone.now()

        super().save(*args, **kwargs)


class OpportunityLineItem(OrgScopedMixin, BaseModel):
    """
    Line item for an opportunity - represents a product or service being quoted.
    Similar to InvoiceLineItem but for the pre-sale stage.
    """

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    product = models.ForeignKey(
        "invoices.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunity_line_items",
    )

    # Item details (can override product info or be custom)
    name = models.CharField(_("Item Name"), max_length=255, blank=True)
    description = models.CharField(_("Description"), max_length=500, blank=True)

    # Quantity and pricing
    quantity = models.DecimalField(
        _("Quantity"), max_digits=10, decimal_places=2, default=1
    )
    unit_price = models.DecimalField(
        _("Unit Price"), max_digits=12, decimal_places=2, default=0
    )

    # Per-item discount
    discount_type = models.CharField(
        _("Discount Type"), max_length=20, choices=DISCOUNT_TYPES, blank=True
    )
    discount_value = models.DecimalField(
        _("Discount Value"), max_digits=12, decimal_places=2, default=0
    )
    discount_amount = models.DecimalField(
        _("Discount Amount"), max_digits=12, decimal_places=2, default=0
    )

    # Computed totals
    subtotal = models.DecimalField(
        _("Subtotal"), max_digits=12, decimal_places=2, default=0
    )
    total = models.DecimalField(_("Total"), max_digits=12, decimal_places=2, default=0)

    # Display order
    order = models.PositiveIntegerField(_("Order"), default=0)

    # Organization (for RLS)
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="opportunity_line_items",
    )

    class Meta:
        verbose_name = "Opportunity Line Item"
        verbose_name_plural = "Opportunity Line Items"
        db_table = "opportunity_line_item"
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["opportunity"]),
            models.Index(fields=["org"]),
        ]

    def __str__(self):
        display_name = self.name if self.name else (self.product.name if self.product else "Item")
        return f"{display_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """Calculate totals before saving."""
        # Get name from product if not set
        if not self.name and self.product:
            self.name = self.product.name

        # Get unit price from product if not set and product exists
        if self.unit_price == 0 and self.product:
            self.unit_price = self.product.price or Decimal("0")

        # Calculate subtotal
        self.subtotal = self.quantity * self.unit_price

        # Calculate discount
        if self.discount_type == "PERCENTAGE":
            self.discount_amount = self.subtotal * (
                self.discount_value / Decimal("100")
            )
        else:
            self.discount_amount = self.discount_value

        # Calculate total (no tax at opportunity stage)
        self.total = self.subtotal - self.discount_amount

        # Ensure org is set from opportunity if not provided
        if not self.org_id and self.opportunity_id:
            self.org_id = self.opportunity.org_id

        # Validate cross-org FK integrity
        if self.opportunity_id and self.org_id:
            if self.opportunity.org_id != self.org_id:
                from django.core.exceptions import ValidationError
                raise ValidationError("OpportunityLineItem.org must match Opportunity.org")
        if self.product_id and self.product.org_id != self.org_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Product must belong to the same organization")

        super().save(*args, **kwargs)

        # Recalculate opportunity amount after saving line item
        if self.opportunity:
            self.opportunity.recalculate_amount()
            self.opportunity.save(update_fields=["amount", "amount_source"])

    def delete(self, *args, **kwargs):
        """Recalculate opportunity amount after deleting line item."""
        opportunity = self.opportunity
        super().delete(*args, **kwargs)

        # Recalculate opportunity amount after deletion
        if opportunity:
            opportunity.recalculate_amount()
            opportunity.save(update_fields=["amount", "amount_source"])


class StageAgingConfig(OrgScopedMixin, BaseModel):
    """Per-org configuration for expected days in each pipeline stage."""

    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="stage_aging_configs",
    )
    stage = models.CharField(_("Stage"), max_length=64, choices=STAGES)
    expected_days = models.PositiveIntegerField(
        _("Expected Days"), default=14
    )
    warning_days = models.PositiveIntegerField(
        _("Warning Days"), null=True, blank=True
    )

    class Meta:
        verbose_name = "Stage Aging Config"
        verbose_name_plural = "Stage Aging Configs"
        db_table = "stage_aging_config"
        unique_together = ("org", "stage")

    def __str__(self):
        return f"{self.org.name} - {self.stage}: {self.expected_days}d"


class SalesGoal(OrgScopedMixin, BaseModel):
    """Sales goal / quota for tracking revenue or deals closed targets."""

    name = models.CharField(_("Goal Name"), max_length=255)
    goal_type = models.CharField(
        _("Goal Type"), max_length=20, choices=GOAL_TYPES
    )
    target_value = models.DecimalField(
        _("Target Value"), max_digits=12, decimal_places=2
    )
    period_type = models.CharField(
        _("Period Type"), max_length=20, choices=PERIOD_TYPES
    )
    period_start = models.DateField(_("Period Start"))
    period_end = models.DateField(_("Period End"))
    assigned_to = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_goals",
    )
    team = models.ForeignKey(
        Teams,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_goals",
    )
    is_active = models.BooleanField(default=True)
    milestone_50_notified = models.BooleanField(default=False)
    milestone_90_notified = models.BooleanField(default=False)
    milestone_100_notified = models.BooleanField(default=False)
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="sales_goals",
    )

    class Meta:
        verbose_name = "Sales Goal"
        verbose_name_plural = "Sales Goals"
        db_table = "sales_goal"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["org", "period_start", "period_end"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_goal_type_display()})"

    def compute_progress(self):
        """Compute current progress toward this goal from CLOSED_WON opportunities.

        Results are cached on the instance to avoid redundant DB queries when
        progress_percent and status are accessed in the same request.
        """
        if hasattr(self, "_cached_progress"):
            return self._cached_progress

        opps = Opportunity.objects.filter(
            org=self.org,
            stage="CLOSED_WON",
            closed_on__gte=self.period_start,
            closed_on__lte=self.period_end,
        )
        if self.assigned_to:
            opps = opps.filter(assigned_to=self.assigned_to)
        elif self.team:
            team_members = Profile.objects.filter(
                user_teams=self.team, is_active=True
            )
            opps = opps.filter(assigned_to__in=team_members)

        if self.goal_type == "REVENUE":
            result = opps.aggregate(
                total=Coalesce(Sum("amount"), Decimal("0"))
            )["total"]
        else:
            result = Decimal(str(opps.count()))

        self._cached_progress = result
        return result

    @property
    def progress_percent(self):
        """Progress as an integer percentage, capped at 100."""
        if not self.target_value or self.target_value == 0:
            return 0
        progress = self.compute_progress()
        return min(int(progress / self.target_value * 100), 100)

    @property
    def status(self):
        """Goal status based on progress vs expected pace."""
        percent = self.progress_percent
        if percent >= 100:
            return "completed"

        today = date.today()
        if today < self.period_start:
            expected_pace = 0
        elif today >= self.period_end:
            expected_pace = 100
        else:
            total_days = (self.period_end - self.period_start).days or 1
            elapsed_days = (today - self.period_start).days
            expected_pace = (elapsed_days / total_days) * 100

        if expected_pace == 0:
            return "on_track"
        if percent >= expected_pace:
            return "on_track"
        if percent >= expected_pace * 0.8:
            return "at_risk"
        return "behind"


# Breakdown type choices for GoalBreakdown
BREAKDOWN_TYPES = (
    ("user", "Por Usuário"),
    ("product", "Por Produto"),
    ("channel", "Por Canal"),
    ("stage", "Por Estágio"),
)


class GoalBreakdown(OrgScopedMixin, BaseModel):
    """
    Desdobramento de meta — permite dividir uma SalesGoal em sub-metas
    por usuário, produto, canal ou estágio do pipeline.

    A soma dos target_value de todos os breakdowns de uma goal deve ser
    igual ao target_value da goal pai (invariante de soma).
    """

    goal = models.ForeignKey(
        SalesGoal,
        on_delete=models.CASCADE,
        related_name="breakdowns",
    )
    breakdown_type = models.CharField(
        _("Tipo de Desdobramento"),
        max_length=20,
        choices=BREAKDOWN_TYPES,
    )
    breakdown_key = models.CharField(
        _("Chave"),
        max_length=255,
        help_text="ID do usuário, produto, canal ou estágio",
    )
    breakdown_label = models.CharField(
        _("Rótulo"),
        max_length=255,
        help_text="Nome legível (ex: nome do usuário, nome do produto)",
    )
    target_value = models.DecimalField(
        _("Meta Parcial"),
        max_digits=12,
        decimal_places=2,
    )
    current_value = models.DecimalField(
        _("Valor Atual"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
    )
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="goal_breakdowns",
    )

    class Meta:
        verbose_name = "Goal Breakdown"
        verbose_name_plural = "Goal Breakdowns"
        db_table = "goal_breakdown"
        ordering = ["breakdown_type", "breakdown_label"]
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["goal", "breakdown_type"]),
        ]
        unique_together = [("goal", "breakdown_type", "breakdown_key")]

    def __str__(self):
        return f"{self.goal.name} → {self.breakdown_label} ({self.get_breakdown_type_display()})"

    @property
    def progress_percent(self):
        """Progress as integer percentage, capped at 100."""
        if not self.target_value or self.target_value == 0:
            return 0
        return min(int(self.current_value / self.target_value * 100), 100)

    @property
    def status(self):
        """Status based on progress vs expected pace (inherits from parent goal period)."""
        percent = self.progress_percent
        if percent >= 100:
            return "completed"

        today = date.today()
        goal = self.goal
        if today < goal.period_start:
            return "on_track"
        if today >= goal.period_end:
            return "behind" if percent < 100 else "completed"

        total_days = (goal.period_end - goal.period_start).days or 1
        elapsed_days = (today - goal.period_start).days
        expected_pace = (elapsed_days / total_days) * 100

        if percent >= expected_pace:
            return "on_track"
        if percent >= expected_pace * 0.8:
            return "at_risk"
        return "behind"


class OpportunityPipeline(OrgScopedMixin, BaseModel):
    """
    Custom pipeline for organizing opportunities into stages (Kanban columns).
    Each organization can have multiple pipelines (e.g., Enterprise Sales, SMB, Renewals).
    """

    name = models.CharField(_("Pipeline Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="opportunity_pipelines"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="If true, new opportunities without explicit pipeline go here",
    )
    is_active = models.BooleanField(default=True)
    visible_to_teams = models.ManyToManyField(
        Teams, blank=True, related_name="visible_opportunity_pipelines",
        help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
    )
    visible_to_users = models.ManyToManyField(
        Profile, blank=True, related_name="visible_opportunity_pipelines",
        help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
    )

    class Meta:
        verbose_name = "Opportunity Pipeline"
        verbose_name_plural = "Opportunity Pipelines"
        db_table = "opportunity_pipeline"
        ordering = ("-is_default", "name")
        indexes = [
            models.Index(fields=["org", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["org"],
                condition=models.Q(is_default=True),
                name="unique_default_opportunity_pipeline_per_org",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.org.name})"


class OpportunityStage(OrgScopedMixin, BaseModel):
    """
    Stage within an Opportunity Pipeline (Kanban column).
    """

    STAGE_TYPE_CHOICES = [
        ("open", "Open"),
        ("won", "Won"),
        ("lost", "Lost"),
    ]

    pipeline = models.ForeignKey(
        OpportunityPipeline, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(_("Stage Name"), max_length=100)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default="#6B7280")
    stage_type = models.CharField(
        max_length=10, choices=STAGE_TYPE_CHOICES, default="open"
    )
    maps_to_stage = models.CharField(
        _("Maps to Legacy Stage"),
        max_length=64,
        choices=STAGES,
        blank=True,
        null=True,
        help_text="When opportunity enters this stage, also update the legacy stage CharField",
    )
    win_probability = models.IntegerField(
        _("Default Win Probability %"),
        default=0,
        help_text="Default probability when opportunity enters this stage",
    )
    wip_limit = models.PositiveIntegerField(
        _("WIP Limit"),
        null=True,
        blank=True,
        help_text="Maximum opportunities allowed in this stage (null = unlimited)",
    )
    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="opportunity_stages"
    )

    class Meta:
        verbose_name = "Opportunity Stage"
        verbose_name_plural = "Opportunity Stages"
        db_table = "opportunity_stage"
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
