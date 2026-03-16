import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext
from rest_framework.permissions import IsAuthenticated

from assistant.models import (
    AutopilotTemplate,
    ChannelDispatch,
    ReminderPolicy,
    ScheduledJob,
    TaskLink,
)
from assistant.presets import get_presets_for_module
from assistant.serializers import (
    AutopilotTemplateSerializer,
    ChannelDispatchSerializer,
    ReminderPolicySerializer,
    ReminderPolicyWriteSerializer,
    ScheduledJobSerializer,
    TaskLinkSerializer,
)

logger = logging.getLogger(__name__)


# ── Reminder Policy ──────────────────────────────────────────────────


class ReminderPolicyListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReminderPolicyWriteSerializer
        return ReminderPolicySerializer

    def get_queryset(self):
        qs = ReminderPolicy.objects.filter(org=self.request.profile.org)

        module_key = self.request.query_params.get("module_key")
        if module_key:
            qs = qs.filter(module_key=module_key)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if target_type and target_id:
            try:
                app_label, model = target_type.split(".")
                ct = ContentType.objects.get(app_label=app_label, model=model)
                qs = qs.filter(target_content_type=ct, target_object_id=target_id)
            except (ValueError, ContentType.DoesNotExist):
                pass

        return qs.order_by("-created_at")


class ReminderPolicyDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ReminderPolicyWriteSerializer
        return ReminderPolicySerializer

    def get_queryset(self):
        return ReminderPolicy.objects.filter(org=self.request.profile.org)


class ReminderPolicyActivateView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def patch(self, request, pk):
        try:
            policy = ReminderPolicy.objects.get(
                pk=pk, org=request.profile.org
            )
        except ReminderPolicy.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        policy.is_active = True
        policy.save(update_fields=["is_active", "updated_at"])

        # Trigger job generation
        from assistant.tasks import recalculate_policy_schedules
        recalculate_policy_schedules.delay(str(policy.id))

        return Response(ReminderPolicySerializer(policy).data)


class ReminderPolicyDeactivateView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def patch(self, request, pk):
        try:
            policy = ReminderPolicy.objects.get(
                pk=pk, org=request.profile.org
            )
        except ReminderPolicy.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        policy.is_active = False
        policy.save(update_fields=["is_active", "updated_at"])

        return Response(ReminderPolicySerializer(policy).data)


# ── Scheduled Jobs ───────────────────────────────────────────────────


class ScheduledJobListView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        qs = ScheduledJob.objects.filter(org=request.profile.org)

        job_status = request.query_params.get("status")
        if job_status:
            qs = qs.filter(status=job_status)

        job_type = request.query_params.get("job_type")
        if job_type:
            qs = qs.filter(job_type=job_type)

        due_gte = request.query_params.get("due_at__gte")
        if due_gte:
            qs = qs.filter(due_at__gte=due_gte)

        due_lte = request.query_params.get("due_at__lte")
        if due_lte:
            qs = qs.filter(due_at__lte=due_lte)

        approval_required = request.query_params.get("approval_required")
        if approval_required is not None:
            qs = qs.filter(approval_required=approval_required.lower() == "true")

        qs = qs.order_by("-due_at")[:100]
        serializer = ScheduledJobSerializer(qs, many=True)
        return Response(serializer.data)


class ScheduledJobDetailView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request, pk):
        try:
            job = ScheduledJob.objects.get(pk=pk, org=request.profile.org)
        except ScheduledJob.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ScheduledJobSerializer(job)
        data = serializer.data
        data["dispatches"] = ChannelDispatchSerializer(
            job.dispatches.all(), many=True
        ).data
        return Response(data)


class ScheduledJobRetryView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, pk):
        try:
            job = ScheduledJob.objects.get(pk=pk, org=request.profile.org)
        except ScheduledJob.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if job.status not in ("failed", "cancelled"):
            return Response(
                {"error": "Only failed or cancelled jobs can be retried."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = "pending"
        job.last_error = ""
        job.save(update_fields=["status", "last_error", "updated_at"])

        return Response(ScheduledJobSerializer(job).data)


class ScheduledJobCancelView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, pk):
        try:
            job = ScheduledJob.objects.get(pk=pk, org=request.profile.org)
        except ScheduledJob.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if job.status != "pending":
            return Response(
                {"error": "Only pending jobs can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = "cancelled"
        job.save(update_fields=["status", "updated_at"])

        return Response(ScheduledJobSerializer(job).data)


class ScheduledJobApproveView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, pk):
        try:
            job = ScheduledJob.objects.get(pk=pk, org=request.profile.org)
        except ScheduledJob.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not job.approval_required or job.status != "pending":
            return Response(
                {"error": "Job is not pending approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.approval_required = False
        job.save(update_fields=["approval_required", "updated_at"])

        return Response(ScheduledJobSerializer(job).data)


# ── Task Links ───────────────────────────────────────────────────────


class TaskLinkListView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        qs = TaskLink.objects.filter(org=request.profile.org)

        source_type = request.query_params.get("source_type")
        source_id = request.query_params.get("source_id")
        if source_type and source_id:
            try:
                app_label, model = source_type.split(".")
                ct = ContentType.objects.get(app_label=app_label, model=model)
                qs = qs.filter(source_content_type=ct, source_object_id=source_id)
            except (ValueError, ContentType.DoesNotExist):
                pass

        task_id = request.query_params.get("task_id")
        if task_id:
            qs = qs.filter(task_id=task_id)

        serializer = TaskLinkSerializer(qs.order_by("-created_at")[:50], many=True)
        return Response(serializer.data)


# ── Runs (consolidated history) ──────────────────────────────────────


class RunsListView(APIView):
    """Consolidated execution history from ScheduledJobs and AutomationLogs."""
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        org = request.profile.org
        source_filter = request.query_params.get("source", "all")

        campaign_id = request.query_params.get("campaign_id")
        results = []

        # Include ScheduledJob completed/failed
        if source_filter in ("all", "reminder", "campaign"):
            jobs_qs = ScheduledJob.objects.filter(
                org=org,
                status__in=["completed", "failed"],
            )
            if source_filter == "reminder":
                jobs_qs = jobs_qs.filter(job_type="reminder")
            elif source_filter == "campaign":
                jobs_qs = jobs_qs.filter(job_type="campaign_step")

            # Filter by campaign_id if provided
            if campaign_id:
                from campaigns.models import Campaign
                campaign_ct = ContentType.objects.get_for_model(Campaign)
                jobs_qs = jobs_qs.filter(
                    source_content_type=campaign_ct,
                    source_object_id=campaign_id,
                )

            for job in jobs_qs.order_by("-updated_at")[:50]:
                results.append({
                    "id": str(job.id),
                    "type": job.job_type,
                    "name": f"Job {job.job_type}",
                    "status": job.status,
                    "executed_at": job.updated_at.isoformat() if job.updated_at else None,
                    "error": job.last_error,
                    "source": "assistant",
                })

        # Include AutomationLog entries
        if source_filter in ("all", "automation"):
            try:
                from automations.models import AutomationLog
                logs_qs = AutomationLog.objects.filter(org=org).order_by("-created_at")[:50]
                for log in logs_qs:
                    results.append({
                        "id": str(log.id),
                        "type": "automation",
                        "name": str(log.automation) if hasattr(log, "automation") else "Automação",
                        "status": log.status,
                        "executed_at": log.created_at.isoformat() if log.created_at else None,
                        "error": getattr(log, "error_detail", ""),
                        "source": "automations",
                    })
            except Exception:
                pass

        # Sort by executed_at descending
        results.sort(key=lambda x: x.get("executed_at") or "", reverse=True)

        return Response(results[:100])


# ── Presets ──────────────────────────────────────────────────────────


class PresetsView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        module = request.query_params.get("module", "")
        if module:
            presets = get_presets_for_module(module)
        else:
            from assistant.presets import ALL_PRESETS
            presets = ALL_PRESETS

        return Response(presets)


# ── Entity Reminders (generic) ──────────────────────────────────────


MODULE_MAP = {
    "leads": "leads",
    "opportunity": "opportunity",
    "cases": "cases",
    "tasks": "tasks",
    "invoices": "invoices",
    "financeiro": "financeiro",
    "orders": "orders",
}


class EntityReminderListCreateView(APIView):
    """Generic list/create reminders for any entity via ContentType."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def _resolve(self, request, target_type, target_id):
        try:
            app_label, model = target_type.split(".")
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist):
            return None, None, None
        model_class = ct.model_class()
        if model_class is None:
            return ct, None, None
        target = model_class.objects.filter(
            pk=target_id, org=request.profile.org
        ).first()
        return ct, target, MODULE_MAP.get(app_label, app_label)

    def get(self, request, target_type, target_id):
        ct, target, _ = self._resolve(request, target_type, target_id)
        if not target:
            return Response(
                {"error": "Entidade não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        policies = ReminderPolicy.objects.filter(
            org=request.profile.org,
            target_content_type=ct,
            target_object_id=target_id,
        ).order_by("-created_at")
        return Response(ReminderPolicySerializer(policies, many=True).data)

    def post(self, request, target_type, target_id):
        ct, target, module_key = self._resolve(request, target_type, target_id)
        if not target:
            return Response(
                {"error": "Entidade não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data.copy()
        data["target_type"] = target_type
        data["target_object_id"] = str(target_id)
        data.setdefault("module_key", module_key)

        serializer = ReminderPolicyWriteSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ReminderPolicySerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


# ── Autopilot Templates ─────────────────────────────────────────────


class AutopilotTemplateListView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        org = request.profile.org
        qs = AutopilotTemplate.objects.filter(org=org)

        module_key = request.query_params.get("module_key")
        if module_key:
            qs = qs.filter(module_key=module_key)

        template_type = request.query_params.get("template_type")
        if template_type:
            qs = qs.filter(template_type=template_type)

        serializer = AutopilotTemplateSerializer(qs.order_by("-created_at"), many=True)
        return Response(serializer.data)
