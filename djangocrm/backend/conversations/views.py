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

from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from channels.registry import ChannelRegistry
from common.permissions import HasOrgContext
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
            "contact", "assigned_to"
        )

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
            queryset = queryset.filter(tags__name=tag)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                contact__first_name__icontains=search
            ) | queryset.filter(contact__last_name__icontains=search)

        serializer = ConversationListSerializer(queryset[:100], many=True)
        return Response(serializer.data)


class ConversationDetailView(APIView):
    """GET/PATCH /api/conversations/<id>/ — Detalhe e atualização."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, pk):
        try:
            conversation = Conversation.objects.select_related(
                "contact", "assigned_to"
            ).get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(ConversationDetailSerializer(conversation).data)

    def patch(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ConversationUpdateSerializer(conversation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
        send_result = {}
        if provider_cls:
            from channels.models import ChannelConfig

            channel_config = ChannelConfig.objects.filter(
                org=request.org, channel_type=channel_type, is_active=True
            ).first()

            if channel_config:
                try:
                    provider = provider_cls()
                    # Enrich message_data with conversation context
                    message_data = dict(request.data)
                    message_data["conversation_id"] = str(conversation.id)
                    send_result = provider.send_message(
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
            sender_name = request.profile.user.get_full_name() or request.profile.user.email

        message = serializer.save(
            org=request.org,
            conversation=conversation,
            sender_name=sender_name,
            sender_id=str(request.user.id) if request.user else "",
        )

        # Atualizar last_message_at
        conversation.last_message_at = message.timestamp
        conversation.save(update_fields=["last_message_at", "updated_at"])

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class ConversationAssignView(APIView):
    """POST /api/conversations/<id>/assign/ e /unassign/"""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, pk, action):
        try:
            conversation = Conversation.objects.get(id=pk, org=request.org)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if action == "assign":
            profile_id = request.data.get("profile_id")
            if not profile_id:
                return Response(
                    {"error": "profile_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            conversation.assigned_to_id = profile_id
        elif action == "unassign":
            conversation.assigned_to = None
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        conversation.save(update_fields=["assigned_to", "updated_at"])
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
            org=request.org, contact_id=contact_id
        ).select_related("assigned_to")

        serializer = ConversationListSerializer(queryset, many=True)
        return Response(serializer.data)
