from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from common.serializers import (
    AttachmentsSerializer,
    CommentSerializer,
    ProfileSerializer,
    TagsSerializer,
    TeamsSerializer,
    UserSerializer,
)
from contacts.serializers import ContactSerializer
from tasks.models import (
    Board,
    BoardColumn,
    BoardMember,
    BoardTask,
    Project,
    Subtask,
    Task,
    TaskDependency,
    TaskPipeline,
    TaskStage,
)


class BoardMemberSerializer(serializers.ModelSerializer):
    """Serializer for board members"""

    profile = ProfileSerializer(read_only=True)
    profile_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = BoardMember
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "board")


class BoardTaskSerializer(serializers.ModelSerializer):
    """Serializer for board tasks"""

    assigned_to = ProfileSerializer(many=True, read_only=True)
    assigned_to_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    is_completed = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = BoardTask
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "completed_at", "org", "column")


class BoardColumnSerializer(serializers.ModelSerializer):
    """Serializer for board columns"""

    tasks = BoardTaskSerializer(many=True, read_only=True)
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = BoardColumn
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "board", "org")

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return obj.tasks.count()


class BoardColumnListSerializer(serializers.ModelSerializer):
    """Simplified column serializer for lists"""

    task_count = serializers.SerializerMethodField()

    class Meta:
        model = BoardColumn
        fields = ["id", "name", "order", "color", "limit", "task_count"]

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return obj.tasks.count()


class BoardSerializer(serializers.ModelSerializer):
    """Serializer for boards"""

    owner = ProfileSerializer(read_only=True)
    columns = BoardColumnListSerializer(many=True, read_only=True)
    members = BoardMemberSerializer(source="memberships", many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "owner",
            "org",
        )

    @extend_schema_field(int)
    def get_member_count(self, obj):
        return obj.members.count()

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return BoardTask.objects.filter(column__board=obj).count()


class BoardListSerializer(serializers.ModelSerializer):
    """Simplified board serializer for lists"""

    owner = ProfileSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    column_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "is_archived",
            "member_count",
            "column_count",
            "task_count",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(int)
    def get_member_count(self, obj):
        return obj.members.count()

    @extend_schema_field(int)
    def get_column_count(self, obj):
        return obj.columns.count()

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return BoardTask.objects.filter(column__board=obj).count()


class SubtaskSerializer(serializers.ModelSerializer):
    """Serializer for subtask checklist items."""

    completed_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Subtask
        fields = [
            "id",
            "title",
            "is_completed",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "order",
            "assigned_to",
            "assigned_to_name",
            "created_at",
        ]
        read_only_fields = ("id", "created_at", "completed_at", "completed_by", "completed_by_name")

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return f"{obj.completed_by.first_name} {obj.completed_by.last_name}".strip() or obj.completed_by.email
        return None

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return str(obj.assigned_to)
        return None


class TaskDependencySerializer(serializers.ModelSerializer):
    """Serializer for task dependencies."""

    depends_on_title = serializers.CharField(source="depends_on.title", read_only=True)
    depends_on_status = serializers.CharField(source="depends_on.status", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = TaskDependency
        fields = [
            "id",
            "task",
            "depends_on",
            "depends_on_title",
            "depends_on_status",
            "task_title",
            "dependency_type",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for projects."""

    owner_name = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    completed_task_count = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "color",
            "status",
            "due_date",
            "owner",
            "owner_name",
            "members",
            "task_count",
            "completed_task_count",
            "progress_percent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_owner_name(self, obj):
        return str(obj.owner) if obj.owner else None

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return obj.tasks.count()

    @extend_schema_field(int)
    def get_completed_task_count(self, obj):
        return obj.tasks.filter(status="Completed").count()

    @extend_schema_field(int)
    def get_progress_percent(self, obj):
        total = obj.tasks.count()
        if total == 0:
            return 0
        completed = obj.tasks.filter(status="Completed").count()
        return round((completed / total) * 100)


class TaskSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    assigned_to = ProfileSerializer(read_only=True, many=True)
    contacts = ContactSerializer(read_only=True, many=True)
    teams = TeamsSerializer(read_only=True, many=True)
    tags = TagsSerializer(read_only=True, many=True)
    task_attachment = AttachmentsSerializer(read_only=True, many=True)
    task_comments = CommentSerializer(read_only=True, many=True)
    subtasks = SubtaskSerializer(many=True, read_only=True)
    subtask_progress = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_blocked = serializers.BooleanField(read_only=True)
    priority_score = serializers.IntegerField(read_only=True)
    dependencies = TaskDependencySerializer(many=True, read_only=True)
    dependents = TaskDependencySerializer(many=True, read_only=True)
    # Related entity names (avoids extra API calls on frontend)
    account_name = serializers.SerializerMethodField()
    opportunity_name = serializers.SerializerMethodField()
    case_name = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "status",
            "priority",
            "due_date",
            "due_time",
            "effort",
            "impact",
            "priority_score",
            "description",
            "account",
            "opportunity",
            "case",
            "lead",
            "project",
            "created_by",
            "created_at",
            "contacts",
            "teams",
            "assigned_to",
            "tags",
            "task_attachment",
            "task_comments",
            "subtasks",
            "subtask_progress",
            "is_overdue",
            "is_blocked",
            "dependencies",
            "dependents",
            # Kanban
            "stage",
            # Related entity names
            "account_name",
            "opportunity_name",
            "case_name",
            "lead_name",
        )

    def get_account_name(self, obj):
        return obj.account.name if obj.account else None

    def get_opportunity_name(self, obj):
        return obj.opportunity.name if obj.opportunity else None

    def get_case_name(self, obj):
        return obj.case.name if obj.case else None

    def get_lead_name(self, obj):
        if not obj.lead:
            return None
        name = f"{obj.lead.first_name or ''} {obj.lead.last_name or ''}".strip()
        return name or obj.lead.title or "Lead"


class TaskCreateSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        request_obj = kwargs.pop("request_obj", None)
        super().__init__(*args, **kwargs)
        self.org = request_obj.profile.org

        self.fields["title"].required = True

    def validate_title(self, title):
        if self.instance:
            if (
                Task.objects.filter(title__iexact=title, org=self.org)
                .exclude(id=self.instance.id)
                .exists()
            ):
                raise serializers.ValidationError("Task already exists with this title")
        else:
            if Task.objects.filter(title__iexact=title, org=self.org).exists():
                raise serializers.ValidationError("Task already exists with this title")
        return title

    def validate(self, attrs):
        """Validate that task has at most one parent entity."""
        attrs = super().validate(attrs)
        parent_fields = ["account", "opportunity", "case", "lead"]
        set_parents = [field for field in parent_fields if attrs.get(field)]
        if len(set_parents) > 1:
            raise serializers.ValidationError(
                {
                    "account": (
                        "A task can only be linked to one parent entity "
                        f"(Account, Opportunity, Case, or Lead). "
                        f"Currently set: {', '.join(set_parents)}"
                    )
                }
            )
        return attrs

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "status",
            "priority",
            "due_date",
            "due_time",
            "effort",
            "impact",
            "description",
            "account",
            "opportunity",
            "case",
            "lead",
            "project",
            "created_by",
            "created_at",
            # Kanban
            "stage",
        )


class TaskDetailEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()
    task_attachment = serializers.FileField()


class TaskCommentEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()


class TaskCreateSwaggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "title",
            "status",
            "priority",
            "due_date",
            "due_time",
            "description",
            "account",
            "opportunity",
            "case",
            "lead",
            "contacts",
            "teams",
            "assigned_to",
            "tags",
        )


# ============================================================================
# Kanban Serializers
# ============================================================================


class TaskStageSerializer(serializers.ModelSerializer):
    """Serializer for task stages."""

    task_count = serializers.SerializerMethodField()

    class Meta:
        model = TaskStage
        fields = [
            "id",
            "name",
            "order",
            "color",
            "stage_type",
            "maps_to_status",
            "wip_limit",
            "task_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "org")

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return obj.tasks.count()

    def validate_name(self, value):
        pipeline = self.context.get("pipeline") or (self.instance.pipeline if self.instance else None)
        if pipeline:
            qs = TaskStage.objects.filter(pipeline=pipeline, name=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Já existe um estágio com este nome neste pipeline.")
        return value


class TaskPipelineSerializer(serializers.ModelSerializer):
    """Serializer for task pipelines with nested stages."""

    stages = TaskStageSerializer(many=True, read_only=True)
    stage_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = TaskPipeline
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "stages",
            "stage_count",
            "task_count",
            "visible_to_teams",
            "visible_to_users",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "org")

    @extend_schema_field(int)
    def get_stage_count(self, obj):
        return obj.stages.count()

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return Task.objects.filter(stage__pipeline=obj).count()


class TaskPipelineListSerializer(serializers.ModelSerializer):
    """Pipeline serializer for lists — includes nested stages for settings dialog."""

    stages = TaskStageSerializer(many=True, read_only=True)
    stage_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = TaskPipeline
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "stages",
            "stage_count",
            "task_count",
            "visible_to_teams",
            "visible_to_users",
            "created_at",
        ]

    @extend_schema_field(int)
    def get_stage_count(self, obj):
        return obj.stages.count()

    @extend_schema_field(int)
    def get_task_count(self, obj):
        return Task.objects.filter(stage__pipeline=obj).count()


class RelatedEntitySerializer(serializers.Serializer):
    """Minimal serializer for related entities on kanban cards."""

    id = serializers.UUIDField()
    name = serializers.CharField()


class TaskKanbanCardSerializer(serializers.ModelSerializer):
    """Lightweight serializer for kanban cards (minimal fields for performance)."""

    assigned_to = ProfileSerializer(read_only=True, many=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_blocked = serializers.BooleanField(read_only=True)
    priority_score = serializers.IntegerField(read_only=True)
    subtask_progress = serializers.CharField(read_only=True)
    related_entity = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "due_date",
            "due_time",
            "effort",
            "impact",
            "priority_score",
            "is_overdue",
            "is_blocked",
            "subtask_progress",
            "stage",
            "kanban_order",
            "assigned_to",
            "related_entity",
            "project",
            "created_at",
        ]

    @extend_schema_field(RelatedEntitySerializer(allow_null=True))
    def get_related_entity(self, obj):
        """Return the related entity (account, lead, opportunity, or case) if any."""
        if obj.account_id:
            return {"id": obj.account_id, "name": obj.account.name, "type": "account"}
        if obj.lead_id:
            return {"id": obj.lead_id, "name": str(obj.lead), "type": "lead"}
        if obj.opportunity_id:
            return {
                "id": obj.opportunity_id,
                "name": obj.opportunity.name,
                "type": "opportunity",
            }
        if obj.case_id:
            return {"id": obj.case_id, "name": obj.case.name, "type": "case"}
        return None


class TaskMoveSerializer(serializers.Serializer):
    """Serializer for moving tasks in kanban."""

    stage_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES, required=False)
    kanban_order = serializers.DecimalField(
        max_digits=15, decimal_places=6, required=False
    )
    above_task_id = serializers.UUIDField(required=False, allow_null=True)
    below_task_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        # Must provide either stage_id or status
        if not attrs.get("stage_id") and not attrs.get("status"):
            raise serializers.ValidationError(
                "Either stage_id or status must be provided"
            )
        return attrs
