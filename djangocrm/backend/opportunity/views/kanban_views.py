"""
Kanban views for opportunity management.
Supports both legacy stage-based (default) and custom pipeline-based kanban boards.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext
from common.pipeline_visibility import filter_visible_pipelines
from common.utils import STAGES
from opportunity.models import (
    Opportunity,
    OpportunityPipeline,
    OpportunityStage,
    StageAgingConfig,
)
from opportunity.serializers import (
    OpportunityKanbanCardSerializer,
    OpportunityMoveSerializer,
    OpportunityPipelineSerializer,
    OpportunityPipelineListSerializer,
    OpportunityStageSerializer,
)


class OpportunityKanbanView(APIView):
    """
    Kanban board view for opportunities.

    Supports two modes:
    1. Legacy stage-based (default): Groups by Opportunity.stage CharField
    2. Pipeline-based: Groups by OpportunityStage when pipeline_id is provided
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunities Kanban"],
        operation_id="opportunities_kanban",
        parameters=[
            OpenApiParameter(name="org", required=True, type=str),
            OpenApiParameter(
                name="pipeline_id",
                description="Pipeline ID. If not provided, uses legacy stage-based columns",
                required=False,
                type=str,
            ),
            OpenApiParameter(name="assigned_to", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
        ],
    )
    def get(self, request):
        """Get kanban board data."""
        org = request.profile.org
        pipeline_id = request.query_params.get("pipeline_id")

        queryset = (
            Opportunity.objects.filter(org=org, is_active=True)
            .select_related("created_by", "account", "pipeline_stage")
            .prefetch_related("assigned_to", "tags")
        )

        # Apply permission filtering
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            queryset = queryset.filter(
                Q(assigned_to=request.profile) | Q(created_by=request.profile.user)
            )

        queryset = self._apply_filters(queryset, request.query_params)

        # Pre-load aging configs to avoid N+1
        aging_configs = {
            c.stage: c
            for c in StageAgingConfig.objects.filter(org=org)
        }

        if pipeline_id:
            return self._get_pipeline_kanban(queryset, pipeline_id, org, aging_configs)
        return self._get_stage_kanban(queryset, aging_configs)

    def _apply_filters(self, queryset, params):
        """Apply common filters to queryset."""
        if params.get("assigned_to"):
            queryset = queryset.filter(assigned_to__id=params["assigned_to"])
        if params.get("search"):
            search = params["search"]
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(account__name__icontains=search)
                | Q(description__icontains=search)
            )
        if params.get("opportunity_type"):
            queryset = queryset.filter(opportunity_type=params["opportunity_type"])
        if params.get("created_at__gte"):
            queryset = queryset.filter(created_at__gte=params["created_at__gte"])
        if params.get("created_at__lte"):
            queryset = queryset.filter(created_at__lte=params["created_at__lte"])
        return queryset

    def _get_stage_kanban(self, queryset, aging_configs):
        """Build kanban data using legacy Opportunity.stage CharField as columns."""
        stage_config = {
            "PROSPECTING": {"order": 1, "color": "#3B82F6", "type": "open"},
            "QUALIFICATION": {"order": 2, "color": "#8B5CF6", "type": "open"},
            "PROPOSAL": {"order": 3, "color": "#F59E0B", "type": "open"},
            "NEGOTIATION": {"order": 4, "color": "#10B981", "type": "open"},
            "CLOSED_WON": {"order": 5, "color": "#22C55E", "type": "won"},
            "CLOSED_LOST": {"order": 6, "color": "#EF4444", "type": "lost"},
        }

        columns = []
        for stage_value, label in STAGES:
            config = stage_config.get(
                stage_value, {"order": 99, "color": "#6B7280", "type": "open"}
            )
            opps = queryset.filter(stage=stage_value).order_by(
                "kanban_order", "-created_at"
            )

            columns.append(
                {
                    "id": stage_value,
                    "name": label,
                    "order": config["order"],
                    "color": config["color"],
                    "stage_type": config["type"],
                    "is_status_column": True,
                    "wip_limit": None,
                    "opportunity_count": opps.count(),
                    "opportunities": OpportunityKanbanCardSerializer(
                        opps[:100], many=True, context={"aging_configs": aging_configs}
                    ).data,
                }
            )

        columns.sort(key=lambda x: x["order"])

        return Response(
            {
                "mode": "status",
                "pipeline": None,
                "columns": columns,
                "total_opportunities": queryset.count(),
            }
        )

    def _get_pipeline_kanban(self, queryset, pipeline_id, org, aging_configs):
        """Build kanban data using OpportunityPipeline stages as columns."""
        pipeline = get_object_or_404(
            OpportunityPipeline, pk=pipeline_id, org=org, is_active=True
        )

        queryset = queryset.filter(pipeline_stage__pipeline=pipeline)

        columns = []
        for stage in pipeline.stages.all().order_by("order"):
            opps = queryset.filter(pipeline_stage=stage).order_by(
                "kanban_order", "-created_at"
            )

            columns.append(
                {
                    "id": str(stage.id),
                    "name": stage.name,
                    "order": stage.order,
                    "color": stage.color,
                    "stage_type": stage.stage_type,
                    "wip_limit": stage.wip_limit,
                    "win_probability": stage.win_probability,
                    "maps_to_stage": stage.maps_to_stage,
                    "is_status_column": False,
                    "opportunity_count": opps.count(),
                    "opportunities": OpportunityKanbanCardSerializer(
                        opps[:100], many=True, context={"aging_configs": aging_configs}
                    ).data,
                }
            )

        return Response(
            {
                "mode": "pipeline",
                "pipeline": OpportunityPipelineListSerializer(pipeline).data,
                "columns": columns,
                "total_opportunities": queryset.count(),
            }
        )


class OpportunityMoveView(APIView):
    """Move an opportunity to a different stage/column and update order."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunities Kanban"],
        operation_id="opportunity_move",
        request=OpportunityMoveSerializer,
    )
    @transaction.atomic
    def patch(self, request, pk):
        """Move opportunity to different column and/or position."""
        org = request.profile.org
        opp = get_object_or_404(Opportunity, pk=pk, org=org)

        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            if not (
                request.profile.user == opp.created_by
                or request.profile in opp.assigned_to.all()
            ):
                return Response(
                    {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
                )

        serializer = OpportunityMoveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Handle pipeline stage change
        if "pipeline_stage_id" in data:
            if data["pipeline_stage_id"]:
                stage = get_object_or_404(
                    OpportunityStage, pk=data["pipeline_stage_id"], org=org
                )

                # Check WIP limit
                if stage.wip_limit:
                    current_count = stage.opportunities.exclude(pk=opp.pk).count()
                    if current_count >= stage.wip_limit:
                        return Response(
                            {
                                "error": f"Stage '{stage.name}' has reached its WIP limit of {stage.wip_limit}"
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                opp.pipeline_stage = stage

                # Auto-update legacy stage if maps_to_stage is set
                if stage.maps_to_stage:
                    opp.stage = stage.maps_to_stage

                # Auto-update probability
                if stage.win_probability and opp.probability == 0:
                    opp.probability = stage.win_probability
            else:
                opp.pipeline_stage = None

        # Handle legacy stage change
        if "stage" in data:
            opp.stage = data["stage"]

        # Calculate new order
        new_order = self._calculate_order(data, opp, org)
        opp.kanban_order = new_order

        opp.save()

        return Response(
            {
                "error": False,
                "message": "Opportunity moved successfully",
                "opportunity": OpportunityKanbanCardSerializer(opp).data,
            }
        )

    def _calculate_order(self, data, opp, org):
        """Calculate the new kanban_order based on position hints."""
        if "kanban_order" in data:
            return data["kanban_order"]

        above_id = data.get("above_opportunity_id")
        below_id = data.get("below_opportunity_id")

        if above_id and below_id:
            above = Opportunity.objects.filter(pk=above_id, org=org).first()
            below = Opportunity.objects.filter(pk=below_id, org=org).first()
            if above and below:
                return (above.kanban_order + below.kanban_order) / 2

        if above_id:
            above = Opportunity.objects.filter(pk=above_id, org=org).first()
            if above:
                if opp.pipeline_stage:
                    next_opp = (
                        Opportunity.objects.filter(
                            org=org,
                            pipeline_stage=opp.pipeline_stage,
                            kanban_order__gt=above.kanban_order,
                        )
                        .order_by("kanban_order")
                        .first()
                    )
                else:
                    next_opp = (
                        Opportunity.objects.filter(
                            org=org,
                            stage=opp.stage,
                            pipeline_stage__isnull=True,
                            kanban_order__gt=above.kanban_order,
                        )
                        .order_by("kanban_order")
                        .first()
                    )

                if next_opp:
                    return (above.kanban_order + next_opp.kanban_order) / 2
                return above.kanban_order + Decimal("1000")

        if below_id:
            below = Opportunity.objects.filter(pk=below_id, org=org).first()
            if below:
                return below.kanban_order - Decimal("1000")

        # Default: append to end
        if opp.pipeline_stage:
            last = (
                Opportunity.objects.filter(pipeline_stage=opp.pipeline_stage, org=org)
                .exclude(pk=opp.pk)
                .order_by("-kanban_order")
                .first()
            )
        else:
            last = (
                Opportunity.objects.filter(
                    stage=opp.stage, pipeline_stage__isnull=True, org=org
                )
                .exclude(pk=opp.pk)
                .order_by("-kanban_order")
                .first()
            )

        if last:
            return last.kanban_order + Decimal("1000")
        return Decimal("1000")


class OpportunityPipelineListCreateView(APIView):
    """List and create opportunity pipelines."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunity Pipelines"],
        responses={200: OpportunityPipelineListSerializer(many=True)},
    )
    def get(self, request):
        """List all pipelines for the organization (filtered by visibility)."""
        org = request.profile.org
        pipelines = (
            OpportunityPipeline.objects.filter(org=org, is_active=True)
            .prefetch_related("stages")
            .annotate(
                _stage_count=Count("stages"),
                _opportunity_count=Count("stages__opportunities"),
            )
        )
        pipelines = filter_visible_pipelines(pipelines, request.profile)
        serializer = OpportunityPipelineListSerializer(pipelines, many=True)
        return Response({"pipelines": serializer.data})

    @extend_schema(
        tags=["Opportunity Pipelines"],
        request=OpportunityPipelineSerializer,
        responses={201: OpportunityPipelineSerializer},
    )
    def post(self, request):
        """Create a new pipeline."""
        org = request.profile.org

        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Only admins can create pipelines"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OpportunityPipelineSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pipeline = serializer.save(org=org, created_by=request.user)

        # Create default stages if requested
        if request.data.get("create_default_stages", True):
            default_stages = [
                {
                    "name": "Prospecção",
                    "order": 1,
                    "color": "#3B82F6",
                    "stage_type": "open",
                    "maps_to_stage": "PROSPECTING",
                    "win_probability": 10,
                },
                {
                    "name": "Qualificação",
                    "order": 2,
                    "color": "#8B5CF6",
                    "stage_type": "open",
                    "maps_to_stage": "QUALIFICATION",
                    "win_probability": 25,
                },
                {
                    "name": "Proposta",
                    "order": 3,
                    "color": "#F59E0B",
                    "stage_type": "open",
                    "maps_to_stage": "PROPOSAL",
                    "win_probability": 50,
                },
                {
                    "name": "Negociação",
                    "order": 4,
                    "color": "#10B981",
                    "stage_type": "open",
                    "maps_to_stage": "NEGOTIATION",
                    "win_probability": 75,
                },
                {
                    "name": "Ganho",
                    "order": 5,
                    "color": "#22C55E",
                    "stage_type": "won",
                    "maps_to_stage": "CLOSED_WON",
                    "win_probability": 100,
                },
                {
                    "name": "Perdido",
                    "order": 6,
                    "color": "#EF4444",
                    "stage_type": "lost",
                    "maps_to_stage": "CLOSED_LOST",
                    "win_probability": 0,
                },
            ]
            for stage_data in default_stages:
                OpportunityStage.objects.create(
                    pipeline=pipeline, org=org, **stage_data
                )

        return Response(
            OpportunityPipelineSerializer(pipeline).data,
            status=status.HTTP_201_CREATED,
        )


class OpportunityPipelineDetailView(APIView):
    """Retrieve, update, delete a pipeline."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get_object(self, pk, org):
        return get_object_or_404(OpportunityPipeline, pk=pk, org=org)

    @extend_schema(
        tags=["Opportunity Pipelines"],
        responses={200: OpportunityPipelineSerializer},
    )
    def get(self, request, pk):
        """Get pipeline details with all stages."""
        pipeline = self.get_object(pk, request.profile.org)
        return Response(OpportunityPipelineSerializer(pipeline).data)

    @extend_schema(
        tags=["Opportunity Pipelines"],
        request=OpportunityPipelineSerializer,
        responses={200: OpportunityPipelineSerializer},
    )
    def put(self, request, pk):
        """Update pipeline."""
        return self._update_pipeline(request, pk)

    def patch(self, request, pk):
        """Partial update pipeline."""
        return self._update_pipeline(request, pk)

    def _update_pipeline(self, request, pk):
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        pipeline = self.get_object(pk, request.profile.org)
        serializer = OpportunityPipelineSerializer(
            pipeline, data=request.data, partial=True
        )

        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pipeline = serializer.save(updated_by=request.user)
        return Response(OpportunityPipelineSerializer(pipeline).data)

    @extend_schema(tags=["Opportunity Pipelines"], responses={204: None})
    def delete(self, request, pk):
        """Delete pipeline (soft delete by setting is_active=False)."""
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        pipeline = self.get_object(pk, request.profile.org)

        opp_count = Opportunity.objects.filter(pipeline_stage__pipeline=pipeline).count()
        if opp_count > 0:
            return Response(
                {
                    "error": f"Cannot delete pipeline with {opp_count} opportunities. Move them first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        was_default = pipeline.is_default
        pipeline.is_default = False
        pipeline.is_active = False
        pipeline.save(update_fields=["is_active", "is_default"])

        # Auto-promote next pipeline if we deleted the default
        if was_default:
            next_pipeline = OpportunityPipeline.objects.filter(
                org=request.profile.org, is_active=True
            ).first()
            if next_pipeline:
                next_pipeline.is_default = True
                next_pipeline.save(update_fields=["is_default"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class OpportunityStageCreateView(APIView):
    """Create a stage in a pipeline."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunity Stages"],
        request=OpportunityStageSerializer,
        responses={201: OpportunityStageSerializer},
    )
    def post(self, request, pipeline_pk):
        """Add a new stage to pipeline."""
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        org = request.profile.org
        pipeline = get_object_or_404(OpportunityPipeline, pk=pipeline_pk, org=org)

        serializer = OpportunityStageSerializer(data=request.data, context={"pipeline": pipeline})
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stage = serializer.save(pipeline=pipeline, org=org, created_by=request.user)
        return Response(
            OpportunityStageSerializer(stage).data, status=status.HTTP_201_CREATED
        )


class OpportunityStageDetailView(APIView):
    """Update or delete a stage."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunity Stages"],
        request=OpportunityStageSerializer,
        responses={200: OpportunityStageSerializer},
    )
    def put(self, request, pk):
        """Update stage."""
        return self._update_stage(request, pk)

    def patch(self, request, pk):
        """Partial update stage."""
        return self._update_stage(request, pk)

    def _update_stage(self, request, pk):
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        stage = get_object_or_404(OpportunityStage, pk=pk, org=request.profile.org)
        serializer = OpportunityStageSerializer(stage, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stage = serializer.save(updated_by=request.user)
        return Response(OpportunityStageSerializer(stage).data)

    @extend_schema(tags=["Opportunity Stages"], responses={204: None})
    def delete(self, request, pk):
        """Delete stage."""
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        stage = get_object_or_404(OpportunityStage, pk=pk, org=request.profile.org)

        opp_count = stage.opportunities.count()
        if opp_count > 0:
            return Response(
                {
                    "error": f"Cannot delete stage with {opp_count} opportunities. Move them first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OpportunityStageReorderView(APIView):
    """Bulk reorder stages in a pipeline."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunity Stages"],
        request=inline_serializer(
            name="OpportunityStageReorderRequest",
            fields={
                "stage_ids": serializers.ListField(child=serializers.UUIDField())
            },
        ),
    )
    @transaction.atomic
    def post(self, request, pipeline_pk):
        """Reorder stages by providing ordered list of stage IDs."""
        if request.profile.role != "ADMIN" and not request.profile.is_admin:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        org = request.profile.org
        pipeline = get_object_or_404(OpportunityPipeline, pk=pipeline_pk, org=org)

        stage_ids = request.data.get("stage_ids", [])

        # Validate all stages belong to this pipeline AND cover all stages
        existing_ids = set(
            str(sid) for sid in
            OpportunityStage.objects.filter(pipeline=pipeline).values_list("id", flat=True)
        )
        provided_ids = set(str(sid) for sid in stage_ids)
        if provided_ids != existing_ids:
            return Response(
                {"error": "Stage IDs must match all stages in this pipeline"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for order, stage_id in enumerate(stage_ids):
            OpportunityStage.objects.filter(id=stage_id).update(order=order)

        return Response({"message": "Stages reordered successfully"})
