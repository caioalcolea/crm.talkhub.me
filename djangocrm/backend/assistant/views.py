import json
import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers, status, viewsets
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext
from rest_framework.permissions import IsAuthenticated

from assistant.models import (
    AssistantMessage,
    AssistantSession,
    AutopilotTemplate,
    ChannelDispatch,
    Notification,
    ReminderPolicy,
    ScheduledJob,
    TaskLink,
)
from assistant.presets import get_presets_for_module
from assistant.serializers import (
    AssistantMessageSerializer,
    AssistantSessionListSerializer,
    AssistantSessionSerializer,
    AutopilotTemplateSerializer,
    ChannelDispatchSerializer,
    JobAttemptSerializer,
    NotificationSerializer,
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

        target_type = request.query_params.get("target_type")
        target_id = request.query_params.get("target_id")
        if target_type and target_id:
            try:
                app_label, model = target_type.split(".")
                ct = ContentType.objects.get(app_label=app_label, model=model)
                qs = qs.filter(target_content_type=ct, target_object_id=target_id)
            except (ValueError, ContentType.DoesNotExist):
                pass

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
        data["attempts"] = JobAttemptSerializer(
            job.attempts.order_by("-attempt_number"), many=True
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


class AutopilotTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasOrgContext]
    serializer_class = AutopilotTemplateSerializer

    def get_queryset(self):
        qs = AutopilotTemplate.objects.filter(org=self.request.profile.org)

        module_key = self.request.query_params.get("module_key")
        if module_key:
            qs = qs.filter(module_key=module_key)

        template_type = self.request.query_params.get("template_type")
        if template_type:
            qs = qs.filter(template_type=template_type)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(org=self.request.profile.org)

    def perform_update(self, serializer):
        if serializer.instance.is_system:
            raise serializers.ValidationError("Modelos do sistema não podem ser editados.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_system:
            raise serializers.ValidationError("Modelos do sistema não podem ser removidos.")
        instance.delete()


# ── AI Generate (copilot) ──────────────────────────────────────────


class AIGenerateView(APIView):
    """Generate autopilot configs from natural language using OpenAI."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request):
        from assistant.ai_service import (
            generate_automation_config,
            generate_campaign_content,
            generate_reminder_config,
        )

        generation_type = request.data.get("type")
        prompt = (request.data.get("prompt") or "").strip()

        if not prompt:
            return Response(
                {"error": "Prompt é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(prompt) > 1000:
            return Response(
                {"error": "Prompt muito longo (máximo 1000 caracteres)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if generation_type == "automation":
            result = generate_automation_config(
                prompt=prompt,
                automation_type=request.data.get("automation_type", "logic_rule"),
                module=request.data.get("module"),
            )
        elif generation_type == "reminder":
            result = generate_reminder_config(
                prompt=prompt,
                module_key=request.data.get("module_key", "financeiro"),
                tipo=request.data.get("tipo"),
            )
        elif generation_type == "campaign":
            result = generate_campaign_content(
                prompt=prompt,
                campaign_type=request.data.get("campaign_type", "email_blast"),
            )
        else:
            return Response(
                {"error": "Tipo inválido. Use: automation, reminder, campaign."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "error" in result:
            return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(result)


# ── Notifications ─────────────────────────────────────────────────────


class NotificationListView(APIView):
    """List notifications with optional filters."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        qs = Notification.objects.filter(
            org=request.profile.org, user=request.profile
        )

        notif_type = request.query_params.get("type")
        if notif_type:
            qs = qs.filter(type=notif_type)

        unread = request.query_params.get("unread")
        if unread and unread.lower() == "true":
            qs = qs.filter(read_at__isnull=True)

        limit = min(int(request.query_params.get("limit", 20)), 50)
        qs = qs.order_by("-created_at")[:limit]
        return Response(NotificationSerializer(qs, many=True).data)


class NotificationUnreadCountView(APIView):
    """Return unread notification count for polling."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        count = Notification.objects.filter(
            org=request.profile.org,
            user=request.profile,
            read_at__isnull=True,
        ).count()
        return Response({"count": count})


class NotificationMarkReadView(APIView):
    """Mark a single notification as read."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(
                pk=pk, org=request.profile.org, user=request.profile
            )
        except Notification.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone as tz
        notif.read_at = tz.now()
        notif.save(update_fields=["read_at", "updated_at"])
        return Response(NotificationSerializer(notif).data)


class NotificationMarkAllReadView(APIView):
    """Mark all unread notifications as read."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request):
        from django.utils import timezone as tz
        updated = Notification.objects.filter(
            org=request.profile.org,
            user=request.profile,
            read_at__isnull=True,
        ).update(read_at=tz.now())
        return Response({"updated": updated})


# ── Assistant Chat (Phase 1 — Conversational Assistant) ──────────────


class AssistantSessionListView(APIView):
    """List user's chat sessions or create a new one."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        sessions = (
            AssistantSession.objects.filter(
                org=request.profile.org, user=request.profile
            )
            .exclude(status="archived")
            .order_by("-last_activity_at")[:50]
        )
        return Response(AssistantSessionListSerializer(sessions, many=True).data)


class AssistantSessionDetailView(APIView):
    """Get session detail with messages, or archive it."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request, pk):
        try:
            session = AssistantSession.objects.get(
                pk=pk, org=request.profile.org, user=request.profile
            )
        except AssistantSession.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(AssistantSessionSerializer(session).data)

    def delete(self, request, pk):
        try:
            session = AssistantSession.objects.get(
                pk=pk, org=request.profile.org, user=request.profile
            )
        except AssistantSession.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        session.status = "archived"
        session.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssistantChatView(APIView):
    """
    Main conversational endpoint.

    POST /api/assistant/chat/
    {
        "session_id": "uuid" | null,
        "message": "user message",
        "context": {"page": "/financeiro", "entity_type": "...", "entity_id": "..."}
    }

    Response:
    {
        "session_id": "uuid",
        "response": "assistant text",
        "proposed_actions": [...],
        "status": "awaiting_confirmation" | "completed" | "error"
    }
    """

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request):
        from assistant.ai_service import build_chat_system_prompt, call_openai_chat
        from assistant.risk import classify_risk, requires_user_approval

        message_text = (request.data.get("message") or "").strip()
        if not message_text:
            return Response(
                {"error": "Mensagem é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(message_text) > 2000:
            return Response(
                {"error": "Mensagem muito longa (máximo 2000 caracteres)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = request.data.get("session_id")
        context = request.data.get("context", {})
        org = request.profile.org
        user = request.profile

        # Get or create session
        if session_id:
            try:
                session = AssistantSession.objects.get(
                    pk=session_id, org=org, user=user
                )
            except AssistantSession.DoesNotExist:
                return Response(
                    {"error": "Sessão não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            session = AssistantSession.objects.create(
                org=org,
                user=user,
                title=message_text[:80],
                context_json=context,
            )

        # Save user message
        user_msg = AssistantMessage.objects.create(
            org=org,
            session=session,
            role="user",
            content=message_text,
        )

        # Build conversation history for LLM
        history = list(
            session.messages.order_by("created_at").values("role", "content")
        )
        # Map internal roles to OpenAI roles
        llm_messages = [{"role": "system", "content": build_chat_system_prompt(context)}]
        for msg in history:
            role = msg["role"]
            if role in ("tool_call", "tool_result", "system"):
                role = "assistant" if role == "tool_call" else "user"
            llm_messages.append({"role": role, "content": msg["content"]})

        # Call LLM
        result = call_openai_chat(
            messages=llm_messages,
            user_id=user.id,
            session=session,
            response_format={"type": "json_object"},
        )

        if result["error"]:
            # Save error as system message
            AssistantMessage.objects.create(
                org=org,
                session=session,
                role="system",
                content=result["error"],
                metadata=result.get("metadata", {}),
            )

            error_status = status.HTTP_429_TOO_MANY_REQUESTS if result.get(
                "metadata", {}
            ).get("rate_limited") else status.HTTP_502_BAD_GATEWAY

            return Response(
                {
                    "session_id": str(session.id),
                    "response": result["error"],
                    "proposed_actions": [],
                    "status": "error",
                },
                status=error_status,
            )

        # Parse LLM response
        try:
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, TypeError):
            parsed = {"message": result["content"] or ""}

        response_text = parsed.get("message", "")
        tool_calls = parsed.get("tool_calls", [])

        # Process tool calls — classify risk and generate previews
        proposed_actions = []
        for tc in tool_calls:
            tool_name = tc.get("tool", "")
            params = tc.get("params", {})
            preview = tc.get("preview", "")

            risk_level, risk_reason = classify_risk(tool_name, params, org)
            needs_approval, approval_reason = requires_user_approval(
                tool_name, params, org
            )

            proposed_actions.append({
                "tool": tool_name,
                "params": params,
                "preview": preview,
                "risk_level": risk_level,
                "risk_reason": risk_reason,
                "requires_approval": needs_approval,
                "approval_reason": approval_reason,
            })

        # Determine status
        if proposed_actions:
            resp_status = "awaiting_confirmation"
        else:
            resp_status = "completed"

        # Save assistant message
        AssistantMessage.objects.create(
            org=org,
            session=session,
            role="assistant",
            content=response_text,
            metadata={
                **result.get("metadata", {}),
                "proposed_actions": proposed_actions,
            },
        )

        return Response({
            "session_id": str(session.id),
            "response": response_text,
            "proposed_actions": proposed_actions,
            "status": resp_status,
        })


class AssistantChatConfirmView(APIView):
    """
    Confirm or cancel proposed actions from the chat.

    POST /api/assistant/chat/confirm/
    {
        "session_id": "uuid",
        "action_index": 0,
        "decision": "apply" | "cancel"
    }
    """

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request):
        from assistant.tools import execute_tool

        session_id = request.data.get("session_id")
        action_index = request.data.get("action_index", 0)
        decision = request.data.get("decision", "cancel")

        if not session_id:
            return Response(
                {"error": "session_id é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = request.profile.org
        user = request.profile

        try:
            session = AssistantSession.objects.get(pk=session_id, org=org, user=user)
        except AssistantSession.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Find the last assistant message with proposed_actions
        last_msg = (
            session.messages.filter(role="assistant")
            .exclude(metadata={})
            .order_by("-created_at")
            .first()
        )

        if not last_msg:
            return Response(
                {"error": "Nenhuma ação pendente encontrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proposed_actions = last_msg.metadata.get("proposed_actions", [])

        if action_index < 0 or action_index >= len(proposed_actions):
            return Response(
                {"error": f"Índice de ação inválido: {action_index}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = proposed_actions[action_index]

        if decision == "cancel":
            # Record cancellation
            AssistantMessage.objects.create(
                org=org,
                session=session,
                role="tool_result",
                content=f"Ação cancelada: {action['tool']}",
                metadata={"action_cancelled": True, "tool": action["tool"]},
            )
            return Response({
                "session_id": str(session.id),
                "result": "cancelled",
                "message": "Ação cancelada.",
            })

        if decision == "apply":
            # Record tool call
            AssistantMessage.objects.create(
                org=org,
                session=session,
                role="tool_call",
                content=json.dumps({"tool": action["tool"], "params": action["params"]}),
                metadata={"tool": action["tool"]},
            )

            # Execute the tool
            tool_result = execute_tool(action["tool"], org, user, action["params"])

            # Record tool result
            AssistantMessage.objects.create(
                org=org,
                session=session,
                role="tool_result",
                content=json.dumps(tool_result, default=str),
                metadata={"tool": action["tool"]},
            )

            if "error" in tool_result:
                return Response({
                    "session_id": str(session.id),
                    "result": "error",
                    "message": tool_result["error"],
                })

            return Response({
                "session_id": str(session.id),
                "result": "applied",
                "message": "Ação executada com sucesso.",
                "data": tool_result.get("result", {}),
            })

        return Response(
            {"error": "Decisão inválida. Use: apply, cancel."},
            status=status.HTTP_400_BAD_REQUEST,
        )
