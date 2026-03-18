from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from common.base import AssignableMixin, BaseModel, OrgScopedMixin
from common.models import Org, Profile, Tags, Teams
from contacts.models import Contact


# Cleanup notes:
# - Removed 'created_on_arrow' property from Task model (frontend computes its own timestamps)


class Board(OrgScopedMixin, BaseModel):
    """Kanban Board"""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="owned_boards"
    )
    members = models.ManyToManyField(
        Profile, through="BoardMember", related_name="boards"
    )
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="boards")
    is_archived = models.BooleanField(default=False)

    # TalkHub Omni integration
    talkhub_list_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="TalkHub Omni ticket list ID",
    )

    class Meta:
        verbose_name = "Board"
        verbose_name_plural = "Boards"
        db_table = "board"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
        ]

    def __str__(self):
        return self.name


class BoardMember(OrgScopedMixin, BaseModel):
    """Board membership with roles"""

    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    )

    board = models.ForeignKey(
        Board, on_delete=models.CASCADE, related_name="memberships"
    )
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="board_memberships"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="board_members",
    )

    class Meta:
        verbose_name = "Board Member"
        verbose_name_plural = "Board Members"
        db_table = "board_member"
        unique_together = ("board", "profile")
        indexes = [
            models.Index(fields=["org", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.profile} - {self.board} ({self.role})"

    def save(self, *args, **kwargs):
        if not self.org_id and self.board_id:
            self.org_id = self.board.org_id
        super().save(*args, **kwargs)


class BoardColumn(OrgScopedMixin, BaseModel):
    """Column in a board (e.g., To Do, In Progress, Done)"""

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default="#6B7280")  # Hex color
    limit = models.PositiveIntegerField(null=True, blank=True)  # WIP limit
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="board_columns",
    )

    # TalkHub Omni integration
    talkhub_stage_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="TalkHub ticket list stage/status ID",
    )

    class Meta:
        verbose_name = "Board Column"
        verbose_name_plural = "Board Columns"
        db_table = "board_column"
        ordering = ("order",)
        unique_together = ("board", "name")
        indexes = [
            models.Index(fields=["org", "order"]),
        ]

    def __str__(self):
        return f"{self.board.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.org_id and self.board_id:
            self.org_id = self.board.org_id
        super().save(*args, **kwargs)


class BoardTask(OrgScopedMixin, BaseModel):
    """Task/Card in a board column"""

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    )

    column = models.ForeignKey(
        BoardColumn, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    assigned_to = models.ManyToManyField(
        Profile, related_name="assigned_board_tasks", blank=True
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Link to CRM entities (optional)
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="board_tasks",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="board_tasks",
    )
    opportunity = models.ForeignKey(
        "opportunity.Opportunity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="board_tasks",
    )
    org = models.ForeignKey(
        Org,
        on_delete=models.CASCADE,
        related_name="board_tasks",
    )

    # TalkHub Omni integration
    talkhub_item_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="TalkHub Omni ticket item ID",
    )
    talkhub_custom_data = models.JSONField(
        default=dict, blank=True,
        help_text="TalkHub ticket custom fields (text1-5, select1-5, etc.)",
    )

    class Meta:
        verbose_name = "Board Task"
        verbose_name_plural = "Board Tasks"
        db_table = "board_task"
        ordering = ("order",)
        indexes = [
            models.Index(fields=["org", "order"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.org_id and self.column_id:
            self.org_id = self.column.board.org_id
        super().save(*args, **kwargs)

    @property
    def is_completed(self):
        return self.completed_at is not None

    @property
    def is_overdue(self):
        if self.due_date and not self.is_completed:
            return timezone.now() > self.due_date
        return False


class TaskPipeline(OrgScopedMixin, BaseModel):
    """
    Custom pipeline for organizing tasks into stages (Kanban columns).
    Each organization can have multiple pipelines (e.g., Development, Support, Marketing).
    """

    name = models.CharField(_("Pipeline Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    org = models.ForeignKey(
        Org, on_delete=models.CASCADE, related_name="task_pipelines"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="If true, new tasks without explicit pipeline go here",
    )
    is_active = models.BooleanField(default=True)
    visible_to_teams = models.ManyToManyField(
        Teams, blank=True, related_name="visible_task_pipelines",
        help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
    )
    visible_to_users = models.ManyToManyField(
        Profile, blank=True, related_name="visible_task_pipelines",
        help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
    )

    class Meta:
        verbose_name = "Task Pipeline"
        verbose_name_plural = "Task Pipelines"
        db_table = "task_pipeline"
        ordering = ("-is_default", "name")
        indexes = [
            models.Index(fields=["org", "-created_at"]),
        ]
        constraints = [
            # Only one default pipeline per org
            models.UniqueConstraint(
                fields=["org"],
                condition=models.Q(is_default=True),
                name="unique_default_task_pipeline_per_org",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.org.name})"


class TaskStage(OrgScopedMixin, BaseModel):
    """
    Stage within a Task Pipeline (Kanban column).
    """

    STAGE_TYPE_CHOICES = [
        ("open", "Open"),  # New tasks
        ("in_progress", "In Progress"),  # Active work
        ("completed", "Completed"),  # Done
    ]

    pipeline = models.ForeignKey(
        TaskPipeline, on_delete=models.CASCADE, related_name="stages"
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
        max_length=50,
        blank=True,
        null=True,
        help_text="When task enters this stage, also update Task.status",
    )

    # Kanban features
    wip_limit = models.PositiveIntegerField(
        _("WIP Limit"),
        null=True,
        blank=True,
        help_text="Maximum tasks allowed in this stage (null = unlimited)",
    )

    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="task_stages")

    class Meta:
        verbose_name = "Task Stage"
        verbose_name_plural = "Task Stages"
        db_table = "task_stage"
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


class Task(AssignableMixin, OrgScopedMixin, BaseModel):
    STATUS_CHOICES = (
        ("New", "Novo"),
        ("In Progress", "Em Andamento"),
        ("Completed", "Concluído"),
    )

    PRIORITY_CHOICES = (("Low", "Baixa"), ("Medium", "Média"), ("High", "Alta"))

    title = models.CharField(_("title"), max_length=200)
    status = models.CharField(_("status"), max_length=50, choices=STATUS_CHOICES)
    priority = models.CharField(_("priority"), max_length=50, choices=PRIORITY_CHOICES)
    due_date = models.DateField(blank=True, null=True)
    due_time = models.TimeField(_("due time"), blank=True, null=True)
    description = models.TextField(_("Notes"), blank=True, null=True)
    account = models.ForeignKey(
        Account,
        related_name="accounts_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    opportunity = models.ForeignKey(
        "opportunity.Opportunity",
        related_name="opportunity_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    case = models.ForeignKey(
        "cases.Case",
        related_name="case_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    lead = models.ForeignKey(
        "leads.Lead",
        related_name="lead_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    contacts = models.ManyToManyField(Contact, related_name="task_contacts")

    # Priority scoring
    effort = models.PositiveSmallIntegerField(
        _("effort"), null=True, blank=True,
        choices=[(1, "Baixo"), (2, "Médio"), (3, "Alto")],
    )
    impact = models.PositiveSmallIntegerField(
        _("impact"), null=True, blank=True,
        choices=[(1, "Baixo"), (2, "Médio"), (3, "Alto")],
    )

    # Project grouping
    project = models.ForeignKey(
        "Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )

    assigned_to = models.ManyToManyField(Profile, related_name="task_assigned_users")
    teams = models.ManyToManyField(Teams, related_name="tasks_teams")
    tags = models.ManyToManyField(Tags, related_name="task_tags", blank=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="tasks")

    # Kanban fields
    kanban_order = models.DecimalField(
        _("Kanban Order"),
        max_digits=15,
        decimal_places=6,
        default=0,
        help_text="Order within the kanban column for drag-drop positioning",
    )
    stage = models.ForeignKey(
        TaskStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text="Custom pipeline stage (if using pipeline mode)",
    )

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        db_table = "task"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["due_date", "due_time"]),
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["status", "kanban_order"]),
            models.Index(fields=["stage", "kanban_order"]),
        ]

    def __str__(self):
        return f"{self.title}"

    def clean(self):
        """Validate that task has at most one parent entity."""
        super().clean()
        parent_fields = ["account", "opportunity", "case", "lead"]
        set_parents = [
            field for field in parent_fields if getattr(self, f"{field}_id", None)
        ]
        if len(set_parents) > 1:
            raise ValidationError(
                {
                    "account": _(
                        "A task can only be linked to one parent entity "
                        "(Account, Opportunity, Case, or Lead). "
                        f"Currently linked to: {', '.join(set_parents)}"
                    )
                }
            )

    def save(self, *args, **kwargs):
        # Validate stage belongs to correct org
        if self.stage_id and self.stage.org_id != self.org_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Task stage must belong to the same organization")
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue (past due date/time and not completed)."""
        if self.status == "Completed":
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
    def priority_score(self) -> int:
        """Computed priority score (higher = more urgent). 0-10 range."""
        score = 0
        priority_map = {"High": 3, "Medium": 2, "Low": 1}
        score += priority_map.get(self.priority, 0)
        if self.impact:
            score += self.impact
        if self.effort:
            score += (4 - self.effort)  # Lower effort = higher score
        if self.is_overdue:
            score += 3
        elif self.due_date == timezone.now().date():
            score += 1
        return min(score, 10)

    @property
    def is_blocked(self) -> bool:
        """True if any blocking dependency is not completed."""
        return self.dependencies.filter(
            dependency_type="blocks"
        ).exclude(
            depends_on__status="Completed"
        ).exists()

    @property
    def subtask_progress(self) -> str:
        """Return subtask completion progress as 'completed/total'."""
        total = self.subtasks.count()
        if total == 0:
            return ""
        completed = self.subtasks.filter(is_completed=True).count()
        return f"{completed}/{total}"


class Subtask(OrgScopedMixin, BaseModel):
    """Checklist item within a Task or Case."""

    task = models.ForeignKey(
        Task,
        related_name="subtasks",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    case = models.ForeignKey(
        "cases.Case",
        related_name="subtasks",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=300)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    order = models.PositiveIntegerField(default=0)
    assigned_to = models.ForeignKey(
        Profile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_subtasks",
    )
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="subtasks")

    class Meta:
        verbose_name = "Subtask"
        verbose_name_plural = "Subtasks"
        db_table = "subtask"
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["task", "order"]),
            models.Index(fields=["case", "order"]),
            models.Index(fields=["org"]),
        ]


class TaskDependency(OrgScopedMixin, BaseModel):
    """Dependency or relationship between two tasks."""

    DEPENDENCY_TYPES = [
        ("blocks", "Bloqueia"),
        ("related", "Relacionada"),
    ]

    task = models.ForeignKey(
        Task, related_name="dependencies", on_delete=models.CASCADE
    )
    depends_on = models.ForeignKey(
        Task, related_name="dependents", on_delete=models.CASCADE
    )
    dependency_type = models.CharField(
        max_length=20, choices=DEPENDENCY_TYPES, default="blocks"
    )
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="task_dependencies")

    class Meta:
        verbose_name = "Task Dependency"
        verbose_name_plural = "Task Dependencies"
        db_table = "task_dependency"
        unique_together = ("task", "depends_on")
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["depends_on"]),
            models.Index(fields=["org"]),
        ]

    def clean(self):
        super().clean()
        if self.task_id == self.depends_on_id:
            raise ValidationError("A task cannot depend on itself.")
        # Check for circular dependencies (max depth 10)
        if self.dependency_type == "blocks":
            self._check_circular(self.depends_on_id, self.task_id, depth=0)

    def _check_circular(self, source_id, target_id, depth):
        if depth > 10:
            return
        deps = TaskDependency.objects.filter(
            task_id=source_id, dependency_type="blocks"
        ).values_list("depends_on_id", flat=True)
        if target_id in deps:
            raise ValidationError("Circular dependency detected.")
        for dep_id in deps:
            self._check_circular(dep_id, target_id, depth + 1)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Project(OrgScopedMixin, BaseModel):
    """Project/Portfolio for grouping tasks."""

    STATUS_CHOICES = [
        ("active", "Ativo"),
        ("completed", "Concluído"),
        ("archived", "Arquivado"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    color = models.CharField(max_length=7, default="#6366F1")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    due_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_projects"
    )
    members = models.ManyToManyField(Profile, related_name="projects", blank=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="projects")

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        db_table = "project"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name
