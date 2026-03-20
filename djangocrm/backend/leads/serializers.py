from rest_framework import serializers

from common.serializers import (
    AttachmentsSerializer,
    LeadCommentSerializer,
    ProfileSerializer,
    TagsSerializer,
    TeamsSerializer,
    UserSerializer,
)
from common.utils import LEAD_STATUS
from contacts.serializers import ContactSerializer
from leads.models import Lead, LeadPipeline, LeadStage


class LeadSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)
    assigned_to = ProfileSerializer(read_only=True, many=True)
    created_by = UserSerializer()
    tags = TagsSerializer(read_only=True, many=True)
    lead_attachment = AttachmentsSerializer(read_only=True, many=True)
    teams = TeamsSerializer(read_only=True, many=True)
    lead_comments = LeadCommentSerializer(read_only=True, many=True)

    # Contact-First computed fields
    primary_contact_name = serializers.SerializerMethodField()
    primary_contact_email = serializers.SerializerMethodField()
    primary_contact_phone = serializers.SerializerMethodField()

    # Activity health computed fields
    days_since_last_contact = serializers.SerializerMethodField()
    is_stale = serializers.SerializerMethodField()
    is_follow_up_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = (
            "id",
            # Core Lead Information
            "title",
            "salutation",
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "website",
            "linkedin_url",
            # Sales Pipeline
            "status",
            "source",
            "industry",
            "rating",
            "opportunity_amount",
            "currency",
            "probability",
            "close_date",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Assignment
            "assigned_to",
            "teams",
            # Activity
            "last_contacted",
            "next_follow_up",
            "description",
            # Related
            "contacts",
            "lead_attachment",
            "lead_comments",
            "tags",
            # System
            "created_by",
            "created_at",
            "is_active",
            "company_name",
            # Kanban
            "stage",
            "kanban_order",
            # Contact-First computed
            "primary_contact_name",
            "primary_contact_email",
            "primary_contact_phone",
            # Activity health computed
            "days_since_last_contact",
            "is_stale",
            "is_follow_up_overdue",
        )

    def get_days_since_last_contact(self, obj):
        return obj.days_since_last_contact

    def get_is_stale(self, obj):
        return obj.is_stale

    def get_is_follow_up_overdue(self, obj):
        return obj.is_follow_up_overdue

    def _get_primary_contact(self, obj):
        """Cache e retorna o primary_contact para evitar queries repetidas."""
        if not hasattr(obj, "_cached_primary_contact"):
            obj._cached_primary_contact = obj.primary_contact
        return obj._cached_primary_contact

    def get_primary_contact_name(self, obj):
        contact = self._get_primary_contact(obj)
        if contact:
            parts = [contact.first_name or "", contact.last_name or ""]
            name = " ".join(p for p in parts if p).strip()
            if name:
                return name
        # Fallback para campos legados
        parts = [obj.first_name or "", obj.last_name or ""]
        return " ".join(p for p in parts if p).strip() or None

    def get_primary_contact_email(self, obj):
        contact = self._get_primary_contact(obj)
        if contact:
            if contact.email:
                return contact.email
            if contact.secondary_email:
                return contact.secondary_email
        return obj.email or None

    def get_primary_contact_phone(self, obj):
        contact = self._get_primary_contact(obj)
        if contact:
            if contact.phone:
                return contact.phone
            if contact.secondary_phone:
                return contact.secondary_phone
        return obj.phone or None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Propagar company_name do account do contato primário
        if not data.get("company_name"):
            contact = self._get_primary_contact(instance)
            if contact and contact.account_id:
                data["company_name"] = contact.account.name
        return data


class LeadCreateSerializer(serializers.ModelSerializer):
    probability = serializers.IntegerField(
        max_value=100, required=False, allow_null=True
    )
    opportunity_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    close_date = serializers.DateField(required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        request_obj = kwargs.pop("request_obj", None)
        super().__init__(*args, **kwargs)
        if self.initial_data and self.initial_data.get("status") == "converted":
            self.fields["email"].required = True
        self.fields["first_name"].required = False
        self.fields["last_name"].required = False
        self.fields["salutation"].required = False
        self.org = request_obj.profile.org

    class Meta:
        model = Lead
        fields = (
            # Core Lead Information
            "title",
            "salutation",
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "website",
            "linkedin_url",
            # Sales Pipeline
            "status",
            "source",
            "industry",
            "rating",
            "opportunity_amount",
            "currency",
            "probability",
            "close_date",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Activity
            "last_contacted",
            "next_follow_up",
            "description",
            # System
            "company_name",
            "is_active",
            # Kanban
            "stage",
        )

    def create(self, validated_data):
        # Default currency from org if not provided and has opportunity_amount
        if not validated_data.get("currency") and validated_data.get(
            "opportunity_amount"
        ):
            request = self.context.get("request")
            if request and hasattr(request, "profile") and request.profile.org:
                validated_data["currency"] = request.profile.org.default_currency
        return super().create(validated_data)


class LeadCreateSwaggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            # Core Lead Information
            "title",
            "salutation",
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "website",
            "linkedin_url",
            # Sales Pipeline
            "status",
            "source",
            "industry",
            "rating",
            "opportunity_amount",
            "probability",
            "close_date",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Assignment & Related
            "assigned_to",
            "teams",
            "contacts",
            "tags",
            # Activity
            "last_contacted",
            "next_follow_up",
            "description",
            # System
            "company_name",
        ]


class CreateLeadFromSiteSwaggerSerializer(serializers.Serializer):
    apikey = serializers.CharField()
    title = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.CharField()
    source = serializers.CharField()
    description = serializers.CharField()


class LeadDetailEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()
    lead_attachment = serializers.FileField()


class LeadCommentEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()


class LeadUploadSwaggerSerializer(serializers.Serializer):
    leads_file = serializers.FileField()


# ============================================
# Kanban Serializers
# ============================================


class LeadStageSerializer(serializers.ModelSerializer):
    """Serializer for lead stages."""

    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadStage
        fields = [
            "id",
            "name",
            "order",
            "color",
            "stage_type",
            "maps_to_status",
            "win_probability",
            "wip_limit",
            "lead_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "org")

    def get_lead_count(self, obj):
        # Use annotation if available, else fallback to query
        if hasattr(obj, '_lead_count'):
            return obj._lead_count
        return obj.leads.count()

    def validate_name(self, value):
        pipeline = self.context.get("pipeline") or (self.instance.pipeline if self.instance else None)
        if pipeline:
            qs = LeadStage.objects.filter(pipeline=pipeline, name=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Já existe um estágio com este nome neste pipeline.")
        return value


class LeadPipelineSerializer(serializers.ModelSerializer):
    """Serializer for lead pipelines with nested stages."""

    stages = LeadStageSerializer(many=True, read_only=True)
    stage_count = serializers.SerializerMethodField()
    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadPipeline
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "auto_create_opportunity",
            "target_opp_pipeline",
            "target_opp_stage",
            "stages",
            "stage_count",
            "lead_count",
            "visible_to_teams",
            "visible_to_users",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "org")

    def get_stage_count(self, obj):
        if hasattr(obj, '_stage_count'):
            return obj._stage_count
        return obj.stages.count()

    def get_lead_count(self, obj):
        if hasattr(obj, '_lead_count'):
            return obj._lead_count
        return Lead.objects.filter(stage__pipeline=obj).count()


class LeadPipelineListSerializer(serializers.ModelSerializer):
    """Pipeline serializer for lists — includes nested stages for settings dialog."""

    stages = LeadStageSerializer(many=True, read_only=True)
    stage_count = serializers.SerializerMethodField()
    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadPipeline
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "auto_create_opportunity",
            "target_opp_pipeline",
            "target_opp_stage",
            "stages",
            "stage_count",
            "lead_count",
            "visible_to_teams",
            "visible_to_users",
            "created_at",
        ]

    def get_stage_count(self, obj):
        if hasattr(obj, '_stage_count'):
            return obj._stage_count
        return obj.stages.count()

    def get_lead_count(self, obj):
        if hasattr(obj, '_lead_count'):
            return obj._lead_count
        return Lead.objects.filter(stage__pipeline=obj).count()


class LeadKanbanCardSerializer(serializers.ModelSerializer):
    """Lightweight serializer for kanban cards (minimal fields for performance)."""

    assigned_to = ProfileSerializer(read_only=True, many=True)
    full_name = serializers.SerializerMethodField()
    days_since_last_contact = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "title",
            "full_name",
            "company_name",
            "email",
            "rating",
            "opportunity_amount",
            "currency",
            "status",
            "stage",
            "kanban_order",
            "last_contacted",
            "next_follow_up",
            "is_follow_up_overdue",
            "days_since_last_contact",
            "assigned_to",
            "created_at",
        ]

    def get_full_name(self, obj):
        return str(obj)

    def get_days_since_last_contact(self, obj):
        return obj.days_since_last_contact


class LeadMoveSerializer(serializers.Serializer):
    """Serializer for moving leads in kanban."""

    stage_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=LEAD_STATUS, required=False)
    kanban_order = serializers.DecimalField(
        max_digits=15, decimal_places=6, required=False
    )
    above_lead_id = serializers.UUIDField(required=False, allow_null=True)
    below_lead_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        # Must provide either stage_id or status
        if not attrs.get("stage_id") and not attrs.get("status"):
            raise serializers.ValidationError(
                "Either stage_id or status must be provided"
            )
        return attrs
