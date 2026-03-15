"""
Views do app conversations.

- ConversationListView: Listar conversas com filtros.
- ConversationDetailView: Detalhe/atualização de conversa.
- MessageListView: Mensagens de uma conversa (cursor-based).
- MessageCreateView: Enviar mensagem.
- ConversationAssignView: Atribuir/desatribuir agente.
- ConversationBotView: Pausar/retomar bot.
- ContactConversationsView: Conversas de um contato.
"""

import logging
import traceback
import uuid

from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from channels.registry import ChannelRegistry
from common.permissions import HasOrgContext, IsOrgAdmin
from conversations.models import Conversation, Message
from conversations.serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    ConversationUpdateSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)


class MessageCursorPagination(CursorPagination):
    page_size = 50
    ordering = "-timestamp"
    cursor_query_param = "cursor"


class ConversationListView(APIView):
    """GET /api/conversations/ — Listar conversas com filtros."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        queryset = Conversation.objects.filter(org=request.org).select_related(
            "contact", "assigned_to__user"
        )

        # Soft-delete filter: default to non-deleted
        show_deleted = request.query_params.get("deleted") == "true"
        queryset = queryset.filter(is_deleted=show_deleted)

        # Filtros
        channel = request.query_params.get("channel")
        if channel:
            queryset = queryset.filter(channel=channel)

        conv_status = request.query_params.get("status")
        if conv_status:
            queryset = queryset.filter(status=conv_status)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        tag = request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__name=tag).distinct()

        # Filter by group/individual conversations
        is_group = request.query_params.get("is_group")
        if is_group == "true":
            queryset = queryset.filter(metadata_json__is_group=True)
        elif is_group == "false":
            queryset = queryset.filter(
                Q(metadata_json__is_group=False) | ~Q(metadata_json__has_key="is_group")
            )

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(contact__first_name__icontains=search)
                | Q(contact__last_name__icontains=search)
                | Q(contact__email__icontains=search)
            )

        # Order: conversations with messages first (by last_message_at), then by created_at
        queryset = queryset.order_by(
            Coalesce("last_message_at", "created_at").desc()
        )

        # Cursor-based pagination (manual, because DRF CursorPagination
        # doesn't support Coalesce expressions natively)
        limit = min(int(request.query_params.get("limit", 50)), 100)
        cursor = request.query_params.get("cursor")  # ISO timestamp

        if cursor:
            from django.utils.dateparse import parse_datetime as _parse_dt
            cursor_dt = _parse_dt(cursor)
            if cursor_dt:
                if not timezone.is_aware(cursor_dt):
                    cursor_dt = timezone.make_aware(cursor_dt)
                queryset = queryset.filter(
                    Q(last_message_at__lt=cursor_dt)
                    | Q(last_message_at__isnull=True, created_at__lt=cursor_dt)
                )

        # Prefetch latest message AFTER pagination filter (optimization)
        queryset = queryset.prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.order_by("-timestamp")[:1],
                to_attr="_latest_messages",
            )
        )

        items = list(queryset[: limit + 1])
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = (last.last_message_at or last.created_at).isoformat()

        return Response({
            "results": ConversationListSerializer(items, many=True).data,
            "next_cursor": next_cursor,
            "has_more": has_more,
        })


class ConversationDetailView(APIView):
    """GET/PATCH /api/conversations/<id>/ — Detalhe e atualização."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, pk):
        try:
            conversation = Conversation.objects.select_related(
                "contact", "assigned_to__user"
            ).get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(ConversationDetailSerializer(conversation).data)

    def patch(self, request, pk):
        try:
            conversation = Conversation.objects.select_related(
                "contact", "assigned_to__user"
            ).get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        old_status = conversation.status
        serializer = ConversationUpdateSerializer(conversation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Mark that status was changed locally so webhooks don't revert it
        new_status = request.data.get("status")
        if new_status and new_status != old_status:
            meta = conversation.metadata_json or {}
            meta["status_changed_locally_at"] = timezone.now().isoformat()
            conversation.metadata_json = meta
            conversation.save(update_fields=["metadata_json"])

            # Sync status to Chatwoot async (fire-and-forget)
            cw_conv_id = meta.get("chatwoot_conversation_id")
            if cw_conv_id and conversation.channel == "chatwoot":
                try:
                    from integrations.tasks import sync_conversation_status_to_chatwoot
                    sync_conversation_status_to_chatwoot.delay(
                        str(request.org.id), cw_conv_id, new_status
                    )
                except Exception:
                    pass  # Non-critical

        # Broadcast via WebSocket
        try:
            from conversations.broadcast import broadcast_conversation_update

            broadcast_conversation_update(
                str(request.org.id),
                ConversationDetailSerializer(conversation).data,
            )
        except Exception:
            pass  # Non-critical

        return Response(ConversationDetailSerializer(conversation).data)


class MessageListView(APIView):
    """GET /api/conversations/<id>/messages/ — Mensagens com cursor pagination."""

    permission_classes = (IsAuthenticated, HasOrgContext)
    pagination_class = MessageCursorPagination

    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        queryset = Message.objects.filter(conversation=conversation).order_by("-timestamp")

        paginator = MessageCursorPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageSerializer(queryset, many=True)
        return Response(serializer.data)


class MessageCreateView(APIView):
    """POST /api/conversations/<id>/messages/ — Enviar mensagem."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.select_related("contact").get(
                id=conversation_id, org=request.org
            )
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        channel_type = request.data.get("channel_type", conversation.channel)

        # Enviar via ChannelProvider se disponível
        provider_cls = ChannelRegistry.get(channel_type)
        if provider_cls:
            from channels.models import ChannelConfig

            channel_config = ChannelConfig.objects.filter(
                org=request.org, channel_type=channel_type, is_active=True
            ).first()

            # Fallback: if no ChannelConfig, try IntegrationConnection
            if not channel_config:
                from integrations.models import IntegrationConnection

                # Map channel_type to connector_slug (they may differ)
                _channel_to_slug = {"smtp_native": "smtp"}
                slug = _channel_to_slug.get(channel_type, channel_type)

                int_conn = IntegrationConnection.objects.filter(
                    org=request.org, connector_slug=slug,
                    is_active=True, is_connected=True,
                ).first()
                if int_conn:
                    channel_config = type(
                        "ProxyConfig", (),
                        {"org": request.org, "config_json": int_conn.config_json},
                    )()

            if channel_config:
                try:
                    provider = provider_cls()
                    # Enrich message_data with conversation context
                    message_data = dict(request.data)
                    message_data["conversation_id"] = str(conversation.id)
                    message_data["idempotency_key"] = f"crm:{uuid.uuid4().hex}"
                    provider.send_message(
                        channel_config, conversation.contact, message_data
                    )
                except Exception as e:
                    logger.error("Failed to send message via %s: %s", channel_type, e)
                    return Response(
                        {"error": f"Failed to send: {e}"},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

        # Criar Message no banco
        sender_name = ""
        if hasattr(request, "profile") and request.profile and request.profile.user:
            sender_name = request.profile.user.email

        # Enrich metadata for email channels
        extra_meta = serializer.validated_data.get("metadata_json") or {}
        if channel_type in ("smtp_native", "email"):
            try:
                contact_email = getattr(conversation.contact, "email", "") if conversation.contact else ""
                conv_meta = conversation.metadata_json or {}
                subject = request.data.get("subject", "") or conv_meta.get("email_subject", "")
                from_email = ""
                try:
                    from channels.providers.smtp_native import _get_smtp_config
                    smtp_cfg = _get_smtp_config(request.org)
                    if smtp_cfg:
                        from_email = smtp_cfg.get("from_email", "")
                except Exception:
                    pass
                extra_meta.update({
                    "email_subject": subject,
                    "email_from": from_email,
                    "email_from_name": sender_name,
                    "email_to": contact_email,
                    "content_type": "text",
                })
            except Exception as e:
                logger.warning("Failed to enrich email metadata: %s", e)

        # Generate idempotency key for outgoing messages
        idem_key = f"crm:{uuid.uuid4().hex}"

        try:
            with transaction.atomic():
                message = serializer.save(
                    org=request.org,
                    conversation=conversation,
                    sender_name=sender_name,
                    sender_id=str(request.user.id) if request.user else "",
                    metadata_json=extra_meta,
                    idempotency_key=idem_key,
                )

                # Re-fetch with lock to prevent concurrent timestamp overwrites
                conv = Conversation.objects.select_for_update().get(pk=conversation.pk)
                if not conv.last_message_at or message.timestamp > conv.last_message_at:
                    conv.last_message_at = message.timestamp
                    conv.save(update_fields=["last_message_at", "updated_at"])
        except Exception as e:
            logger.error(
                "Failed to save message for conversation %s: %s",
                conversation_id, e, exc_info=True,
            )
            traceback.print_exc()
            return Response(
                {"error": f"Erro ao salvar mensagem: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Broadcast via WebSocket (outside save try/except for clear error separation)
        try:
            from conversations.broadcast import broadcast_new_message

            broadcast_new_message(
                str(request.org.id),
                str(conversation.id),
                MessageSerializer(message).data,
            )
        except Exception:
            pass  # Non-critical — clients will catch up via polling

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class ConversationAssignView(APIView):
    """POST /api/conversations/<id>/assign/ e /unassign/"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, pk, action):
        try:
            conversation = Conversation.objects.select_related(
                "contact", "assigned_to__user"
            ).get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if action == "assign":
            profile_id = request.data.get("profile_id")
            if not profile_id:
                return Response(
                    {"error": "profile_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Validate profile exists
            from common.models import Profile
            try:
                profile = Profile.objects.select_related("user").get(
                    id=profile_id, org=request.org
                )
            except Profile.DoesNotExist:
                return Response(
                    {"error": "Profile not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            conversation.assigned_to = profile
        elif action == "unassign":
            conversation.assigned_to = None
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        conversation.save(update_fields=["assigned_to", "updated_at"])

        # Single re-query with all relations (no redundant refresh_from_db)
        conversation = Conversation.objects.select_related(
            "contact", "assigned_to__user"
        ).get(id=pk, org=request.org)

        return Response(ConversationDetailSerializer(conversation).data)


class ConversationBotView(APIView):
    """POST /api/conversations/<id>/bot/pause/ e /bot/resume/"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, pk, action):
        try:
            conversation = Conversation.objects.select_related("contact").get(
                id=pk, org=request.org
            )
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        user_ns = conversation.omni_user_ns
        if not user_ns:
            return Response(
                {"error": "No omni_user_ns for this conversation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delegar para TalkHub Omni provider se disponível
        provider_cls = ChannelRegistry.get("talkhub_omni")
        if not provider_cls:
            return Response(
                {"error": "TalkHub Omni provider not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Bot pause/resume será implementado no TalkHub Omni connector
        return Response({"status": f"bot_{action}", "user_ns": user_ns})


class ContactConversationsView(APIView):
    """GET /api/contacts/<id>/conversations/ — Conversas de um contato."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, contact_id):
        queryset = Conversation.objects.filter(
            org=request.org, contact_id=contact_id, is_deleted=False
        ).select_related(
            "contact", "assigned_to__user"
        ).prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.order_by("-timestamp")[:1],
                to_attr="_latest_messages",
            )
        ).order_by(Coalesce("last_message_at", "created_at").desc())

        serializer = ConversationListSerializer(queryset[:50], many=True)
        return Response(serializer.data)


class ConversationUpdatesView(APIView):
    """
    GET /api/conversations/updates/?since=<iso_timestamp>

    Lightweight poll endpoint for real-time updates.
    Returns conversations updated since the given timestamp.
    Much lighter than re-fetching the full list.
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        since = request.query_params.get("since")
        conversation_id = request.query_params.get("conversation_id")

        if not since:
            return Response({"conversations": [], "messages": []})

        try:
            from django.utils.dateparse import parse_datetime
            since_dt = parse_datetime(since)
            if not since_dt:
                return Response({"error": "Invalid timestamp"}, status=status.HTTP_400_BAD_REQUEST)
            if not timezone.is_aware(since_dt):
                since_dt = timezone.make_aware(since_dt)
        except (ValueError, TypeError):
            return Response({"error": "Invalid timestamp"}, status=status.HTTP_400_BAD_REQUEST)

        # Get conversations updated since timestamp (exclude soft-deleted)
        updated_convs = Conversation.objects.filter(
            org=request.org,
            updated_at__gt=since_dt,
            is_deleted=False,
        )

        # Filter by group/individual to match frontend tab
        is_group = request.query_params.get("is_group")
        if is_group == "true":
            updated_convs = updated_convs.filter(metadata_json__is_group=True)
        elif is_group == "false":
            updated_convs = updated_convs.filter(
                Q(metadata_json__is_group=False) | ~Q(metadata_json__has_key="is_group")
            )

        updated_convs = updated_convs.select_related("contact", "assigned_to__user").prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.order_by("-timestamp")[:1],
                to_attr="_latest_messages",
            )
        ).order_by("-updated_at")[:20]

        conv_data = ConversationListSerializer(updated_convs, many=True).data

        # If a specific conversation is being watched, return new messages
        new_messages = []
        if conversation_id:
            msgs = Message.objects.filter(
                org=request.org,
                conversation_id=conversation_id,
                timestamp__gt=since_dt,
            ).order_by("timestamp")[:50]
            new_messages = MessageSerializer(msgs, many=True).data

        return Response({
            "conversations": conv_data,
            "messages": new_messages,
            "server_time": timezone.now().isoformat(),
        })


class ConversationSoftDeleteView(APIView):
    """POST /api/conversations/<id>/delete/ — Soft-delete (any user).
       POST /api/conversations/<id>/restore/ — Restore (admin only)."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, pk, action):
        try:
            conversation = Conversation.objects.get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if action == "delete":
            if conversation.is_deleted:
                return Response({"error": "Already deleted"}, status=status.HTTP_400_BAD_REQUEST)
            conversation.is_deleted = True
            conversation.deleted_at = timezone.now()
            conversation.deleted_by = getattr(request, "profile", None)
            conversation.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
            return Response({"message": "Conversa movida para deletados."})

        elif action == "restore":
            # Admin only
            profile = getattr(request, "profile", None)
            if not profile or (profile.role != "ADMIN" and not profile.is_admin):
                return Response(
                    {"error": "Apenas administradores podem restaurar conversas."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not conversation.is_deleted:
                return Response({"error": "Not deleted"}, status=status.HTTP_400_BAD_REQUEST)
            conversation.is_deleted = False
            conversation.deleted_at = None
            conversation.deleted_by = None
            conversation.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
            return Response({"message": "Conversa restaurada."})

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)


class ConversationPermanentDeleteView(APIView):
    """DELETE /api/conversations/<id>/permanent-delete/ — Admin only, must be soft-deleted first."""

    permission_classes = (IsAuthenticated, HasOrgContext, IsOrgAdmin)

    def delete(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if not conversation.is_deleted:
            return Response(
                {"error": "A conversa deve estar na lixeira antes de ser excluída permanentemente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation.delete()  # CASCADE deletes messages too
        return Response(status=status.HTTP_204_NO_CONTENT)
