"""
TalkHub Omni API views — refatorado para o sistema integrativo v2.

Módulos:
1. Connection (status, credentials, connect, disconnect)
2. Channels (CRUD canais Omni)
3. Sync Config (configuração de sync)
4. Contact Sync (sync, push, enrich)
5. Messaging (send text, sms, email, content, template, broadcast, flow)
6. Opt-in/Opt-out (sms, email)
7. Tags & Labels
8. Tickets (sync, mapping)
9. Team Members
10. Bot Control
11. Analytics
12. Workspace / Flows
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import HasOrgContext
from contacts.models import Contact

from .client import TalkHubAPIError, TalkHubClient
from .models import (
    TalkHubConnection,
    TalkHubOmniChannel,
    TalkHubSyncConfig,
    TalkHubSyncJob,
    TalkHubTeamMember,
    TalkHubTicketListMapping,
)
from .serializers import (
    AssignAgentSerializer,
    AssignGroupSerializer,
    LabelActionSerializer,
    LogEventSerializer,
    OptInOutSerializer,
    SendBroadcastSerializer,
    SendContentSerializer,
    SendEmailSerializer,
    SendFlowSerializer,
    SendSMSSerializer,
    SendTextSerializer,
    SendWhatsAppTemplateSerializer,
    TagActionSerializer,
    TalkHubCredentialsSerializer,
    TalkHubOmniChannelSerializer,
    TalkHubSyncConfigSerializer,
    TalkHubSyncHistorySerializer,
    TalkHubSyncJobSerializer,
    TalkHubTeamMemberSerializer,
    TalkHubTicketListMappingSerializer,
    UserFieldsSerializer,
)

logger = logging.getLogger(__name__)


def _get_org(request):
    """Get org from request. Returns None if no org context (HasOrgContext will block this)."""
    return request.org


def _get_client_for_request(request):
    org = _get_org(request)
    conn = TalkHubConnection.objects.filter(org=org, is_connected=True).first()
    if not conn:
        return None, Response(
            {"error": "TalkHub Omni is not connected"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return TalkHubClient(api_key=conn.api_key, base_url=conn.workspace_url), None


def _get_contact_with_subscriber(request, contact_id):
    org = _get_org(request)
    contact = Contact.objects.filter(org=org, id=contact_id).first()
    if not contact:
        return None, None, Response(
            {"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND
        )
    if not contact.talkhub_subscriber_id:
        return contact, None, Response(
            {"error": "Contact is not linked to a TalkHub subscriber"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return contact, contact.talkhub_subscriber_id, None


# ══════════════════════════════════════════════════════════════════════
# MODULE 1 — Connection
# ══════════════════════════════════════════════════════════════════════


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def talkhub_status(request):
    """GET /talkhub/status/ — connection status."""
    org = _get_org(request)
    conn = TalkHubConnection.objects.filter(org=org).first()
    if not conn or not conn.is_connected:
        return Response({"connected": False})
    return Response({
        "connected": True,
        "workspace_name": conn.workspace_name,
        "workspace_url": conn.workspace_url,
        "owner_email": conn.owner_email,
        "last_sync_at": conn.last_sync_at,
        "connected_at": conn.created_at,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def talkhub_credentials(request):
    """POST /talkhub/credentials/ — save API key."""
    ser = TalkHubCredentialsSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    org = _get_org(request)
    conn, _ = TalkHubConnection.objects.get_or_create(org=org)
    conn.api_key = ser.validated_data["api_key"]
    conn.workspace_url = ser.validated_data.get("workspace_url", "https://chat.talkhub.me")
    conn.save(update_fields=["api_key", "workspace_url", "updated_at"])
    return Response({"status": "credentials_saved"})


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def talkhub_connect(request):
    """POST /talkhub/connect/ — validate API Key via GET /team-info."""
    org = _get_org(request)
    conn = TalkHubConnection.objects.filter(org=org).first()
    if not conn or not conn.api_key:
        return Response(
            {"error": "No credentials saved"}, status=status.HTTP_400_BAD_REQUEST
        )
    client = TalkHubClient(api_key=conn.api_key, base_url=conn.workspace_url)
    try:
        info = client.get_team_info()
    except TalkHubAPIError as exc:
        return Response({"error": f"Failed to connect: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

    conn.is_connected = True
    conn.workspace_name = info.get("name") or info.get("team_name", "")
    conn.owner_email = info.get("email") or info.get("owner_email", "")
    conn.connected_by = request.profile
    conn.save(update_fields=[
        "is_connected", "workspace_name", "owner_email", "connected_by", "updated_at",
    ])
    return Response({"connected": True, "workspace_name": conn.workspace_name})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, HasOrgContext])
def talkhub_disconnect(request):
    """DELETE /talkhub/disconnect/."""
    org = _get_org(request)
    TalkHubConnection.objects.filter(org=org).update(is_connected=False, api_key="")
    return Response({"disconnected": True})


# ══════════════════════════════════════════════════════════════════════
# MODULE 2 — Channels
# ══════════════════════════════════════════════════════════════════════


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def channel_config_list(request):
    """GET list / POST create channel config."""
    org = _get_org(request)
    if request.method == "GET":
        channels = TalkHubOmniChannel.objects.filter(org=org)
        return Response(TalkHubOmniChannelSerializer(channels, many=True).data)

    ser = TalkHubOmniChannelSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save(org=org)
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated, HasOrgContext])
def channel_config_detail(request, channel_id):
    """PUT update / DELETE channel config."""
    org = _get_org(request)
    channel = TalkHubOmniChannel.objects.filter(org=org, id=channel_id).first()
    if not channel:
        return Response({"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        channel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    ser = TalkHubOmniChannelSerializer(channel, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def channel_test(request, channel_id):
    """POST /talkhub/channels/{id}/test/ — test channel connection."""
    org = _get_org(request)
    channel = TalkHubOmniChannel.objects.filter(org=org, id=channel_id).first()
    if not channel:
        return Response({"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)

    api_key = channel.api_key
    if not api_key:
        conn = TalkHubConnection.objects.filter(org=org, is_connected=True).first()
        api_key = conn.api_key if conn else ""

    if not api_key:
        return Response({"error": "No API key"}, status=status.HTTP_400_BAD_REQUEST)

    client = TalkHubClient(api_key=api_key)
    try:
        client.get_team_info()
        channel.is_connected = True
        channel.last_tested_at = timezone.now()
        channel.save(update_fields=["is_connected", "last_tested_at", "updated_at"])
        return Response({"status": "connected"})
    except TalkHubAPIError as exc:
        channel.is_connected = False
        channel.last_tested_at = timezone.now()
        channel.save(update_fields=["is_connected", "last_tested_at", "updated_at"])
        return Response({"status": "failed", "error": str(exc)})


# ══════════════════════════════════════════════════════════════════════
# MODULE 3 — Sync Config
# ══════════════════════════════════════════════════════════════════════


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated, HasOrgContext])
def sync_config(request):
    """GET/PUT sync configuration."""
    org = _get_org(request)
    config, _ = TalkHubSyncConfig.objects.get_or_create(org=org)

    if request.method == "GET":
        return Response(TalkHubSyncConfigSerializer(config).data)

    ser = TalkHubSyncConfigSerializer(config, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def sync_now(request):
    """POST /talkhub/sync/now/ — trigger immediate sync."""
    org = _get_org(request)
    sync_type = request.data.get("sync_type", "contacts")

    conn = TalkHubConnection.objects.filter(org=org, is_connected=True).first()
    if not conn:
        return Response({"error": "TalkHub not connected"}, status=status.HTTP_400_BAD_REQUEST)

    job = TalkHubSyncJob.objects.create(org=org, sync_type=sync_type)

    from .tasks import (
        sync_omni_contacts, sync_omni_tickets, sync_omni_tags,
        sync_omni_team_members, sync_omni_statistics,
    )

    task_map = {
        "contacts": sync_omni_contacts,
        "tickets": sync_omni_tickets,
    }
    task_fn = task_map.get(sync_type)
    if task_fn:
        task_fn.delay(str(org.id), str(job.id))
    elif sync_type == "tags":
        sync_omni_tags.delay(str(org.id))
    elif sync_type == "team_members":
        sync_omni_team_members.delay(str(org.id))
    elif sync_type == "statistics":
        sync_omni_statistics.delay(str(org.id))
    elif sync_type == "all":
        # Disparar todos os tipos de sync
        sync_omni_contacts.delay(str(org.id), str(job.id))
        sync_omni_tickets.delay(
            str(org.id),
            str(TalkHubSyncJob.objects.create(org=org, sync_type="tickets").id),
        )
        sync_omni_tags.delay(str(org.id))
        sync_omni_team_members.delay(str(org.id))
        sync_omni_statistics.delay(str(org.id))

    return Response(
        {"job": TalkHubSyncJobSerializer(job).data},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def sync_history(request):
    """GET /talkhub/sync/history/ — últimos 50 sync jobs."""
    org = _get_org(request)
    sync_type = request.query_params.get("type")
    qs = TalkHubSyncJob.objects.filter(org=org).order_by("-created_at")[:50]
    if sync_type:
        qs = qs.filter(sync_type=sync_type)
    return Response({"jobs": TalkHubSyncHistorySerializer(qs, many=True).data})


# ══════════════════════════════════════════════════════════════════════
# MODULE 4 — Contact Sync
# ══════════════════════════════════════════════════════════════════════


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def sync_contacts_start(request):
    """POST /talkhub/sync/contacts/ — start contact import."""
    org = _get_org(request)
    conn = TalkHubConnection.objects.filter(org=org, is_connected=True).first()
    if not conn:
        return Response({"error": "TalkHub not connected"}, status=status.HTTP_400_BAD_REQUEST)

    job = TalkHubSyncJob.objects.create(org=org, sync_type="contacts")
    from .tasks import sync_omni_contacts
    sync_omni_contacts.delay(str(org.id), str(job.id))
    return Response({"job": TalkHubSyncJobSerializer(job).data}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def sync_job_status(request, job_id):
    """GET /talkhub/sync/jobs/{jobId}/ — poll any sync job."""
    org = _get_org(request)
    job = TalkHubSyncJob.objects.filter(org=org, id=job_id).first()
    if not job:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"job": TalkHubSyncJobSerializer(job).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_push(request, contact_id):
    """POST /talkhub/contacts/{id}/push/ — push CRM contact to TalkHub."""
    from .sync_engine import push_contact_to_talkhub

    org = _get_org(request)
    contact = Contact.objects.filter(org=org, id=contact_id).first()
    if not contact:
        return Response({"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        result = push_contact_to_talkhub(org, contact)
        return Response({"status": result})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_chat_history(request, contact_id):
    """GET /talkhub/contacts/{id}/chat-history/."""
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.get_chat_messages(user_ns))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════
# MODULE 5 — Messaging
# ══════════════════════════════════════════════════════════════════════


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_text(request, contact_id):
    """POST /talkhub/contacts/{id}/send/text/."""
    ser = SendTextSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        result = client.send_text(user_ns, ser.validated_data["content"])
        return Response(result)
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_sms(request, contact_id):
    """POST /talkhub/contacts/{id}/send/sms/."""
    ser = SendSMSSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    if not getattr(contact, "sms_opt_in", False):
        return Response({"error": "Contact has not opted in to SMS"}, status=status.HTTP_403_FORBIDDEN)
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.send_sms(user_ns, ser.validated_data["content"]))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_email(request, contact_id):
    """POST /talkhub/contacts/{id}/send/email/."""
    ser = SendEmailSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    if not getattr(contact, "email_opt_in", False):
        return Response({"error": "Contact has not opted in to email"}, status=status.HTTP_403_FORBIDDEN)
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.send_email(user_ns, ser.validated_data["content"], ser.validated_data.get("subject", "")))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_content(request, contact_id):
    """POST /talkhub/contacts/{id}/send/content/."""
    ser = SendContentSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.send_content(user_ns, ser.validated_data))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_whatsapp_template(request, contact_id):
    """POST /talkhub/contacts/{id}/send/whatsapp-template/."""
    ser = SendWhatsAppTemplateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.send_whatsapp_template(user_ns, ser.validated_data))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def whatsapp_templates(request):
    """GET /talkhub/whatsapp-templates/."""
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.list_whatsapp_templates())
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_broadcast(request):
    """POST /talkhub/send/broadcast/."""
    ser = SendBroadcastSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.send_broadcast(ser.validated_data))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def send_flow(request, contact_id):
    """POST /talkhub/contacts/{id}/send/flow/."""
    ser = SendFlowSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        if ser.validated_data["flow_type"] == "main":
            return Response(client.send_main_flow(user_ns, ser.validated_data["flow_ns"]))
        return Response(client.send_sub_flow(user_ns, ser.validated_data["flow_ns"]))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════
# MODULE 6 — Opt-in / Opt-out
# ══════════════════════════════════════════════════════════════════════


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def opt_in_out(request, contact_id):
    """POST /talkhub/contacts/{id}/opt/ — opt-in or opt-out sms/email."""
    ser = OptInOutSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err

    channel = ser.validated_data["channel"]
    action = ser.validated_data["action"]

    try:
        method_map = {
            ("sms", "opt_in"): client.opt_in_sms,
            ("sms", "opt_out"): client.opt_out_sms,
            ("email", "opt_in"): client.opt_in_email,
            ("email", "opt_out"): client.opt_out_email,
        }
        result = method_map[(channel, action)](user_ns)

        # Atualizar flag no Contact
        if channel == "sms":
            contact.sms_opt_in = action == "opt_in"
            contact.save(update_fields=["sms_opt_in", "updated_at"])
        elif channel == "email":
            contact.email_opt_in = action == "opt_in"
            contact.save(update_fields=["email_opt_in", "updated_at"])

        return Response({"status": f"{channel}_{action}", "result": result})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════
# MODULE 7 — Tags & Labels
# ══════════════════════════════════════════════════════════════════════


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_tags_add(request, contact_id):
    """POST /talkhub/contacts/{id}/tags/add/."""
    ser = TagActionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.add_tags_by_name(user_ns, ser.validated_data["tags"])
        return Response({"status": "tags_added"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_tags_remove(request, contact_id):
    """DELETE /talkhub/contacts/{id}/tags/remove/."""
    ser = TagActionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.remove_tags_by_name(user_ns, ser.validated_data["tags"])
        return Response({"status": "tags_removed"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_labels_add(request, contact_id):
    """POST /talkhub/contacts/{id}/labels/add/."""
    ser = LabelActionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.add_labels_by_name(user_ns, ser.validated_data["labels"])
        return Response({"status": "labels_added"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_labels_remove(request, contact_id):
    """DELETE /talkhub/contacts/{id}/labels/remove/."""
    ser = LabelActionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.remove_labels_by_name(user_ns, ser.validated_data["labels"])
        return Response({"status": "labels_removed"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════
# MODULE 8 — Tickets
# ══════════════════════════════════════════════════════════════════════


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def sync_tickets_start(request):
    """POST /talkhub/sync/tickets/ — start ticket sync."""
    org = _get_org(request)
    conn = TalkHubConnection.objects.filter(org=org, is_connected=True).first()
    if not conn:
        return Response({"error": "TalkHub not connected"}, status=status.HTTP_400_BAD_REQUEST)
    job = TalkHubSyncJob.objects.create(org=org, sync_type="tickets")
    from .tasks import sync_omni_tickets
    sync_omni_tickets.delay(str(org.id), str(job.id))
    return Response({"job": TalkHubSyncJobSerializer(job).data}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated, HasOrgContext])
def ticket_list_mappings(request):
    """GET list / PUT update ticket list mappings."""
    org = _get_org(request)
    if request.method == "GET":
        mappings = TalkHubTicketListMapping.objects.filter(org=org)
        return Response(TalkHubTicketListMappingSerializer(mappings, many=True).data)

    # PUT — bulk update
    for item in request.data:
        mapping_id = item.get("id")
        if not mapping_id:
            continue
        mapping = TalkHubTicketListMapping.objects.filter(org=org, id=mapping_id).first()
        if mapping:
            ser = TalkHubTicketListMappingSerializer(mapping, data=item, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
    return Response({"status": "updated"})


# ══════════════════════════════════════════════════════════════════════
# MODULE 9 — Team Members
# ══════════════════════════════════════════════════════════════════════


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def team_members_list(request):
    """GET /talkhub/team-members/ — list synced team members."""
    org = _get_org(request)
    members = TalkHubTeamMember.objects.filter(org=org)
    return Response(TalkHubTeamMemberSerializer(members, many=True).data)


# ══════════════════════════════════════════════════════════════════════
# MODULE 10 — Bot Control
# ══════════════════════════════════════════════════════════════════════


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_pause_bot(request, contact_id):
    """POST /talkhub/contacts/{id}/pause-bot/."""
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.pause_bot(user_ns)
        return Response({"status": "bot_paused"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_resume_bot(request, contact_id):
    """POST /talkhub/contacts/{id}/resume-bot/."""
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.resume_bot(user_ns)
        return Response({"status": "bot_resumed"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_log_event(request, contact_id):
    """POST /talkhub/contacts/{id}/log-event/."""
    ser = LogEventSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.log_custom_event(user_ns, ser.validated_data)
        return Response({"status": "event_logged"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_user_fields(request, contact_id):
    """PUT /talkhub/contacts/{id}/user-fields/."""
    ser = UserFieldsSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.set_user_fields_by_name(user_ns, ser.validated_data["fields"])
        return Response({"status": "fields_updated"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_assign_agent(request, contact_id):
    """POST /talkhub/contacts/{id}/assign-agent/."""
    ser = AssignAgentSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.assign_agent(user_ns, ser.validated_data["agent_id"])
        return Response({"status": "agent_assigned"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_unassign_agent(request, contact_id):
    """POST /talkhub/contacts/{id}/unassign-agent/."""
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.unassign_agent(user_ns)
        return Response({"status": "agent_unassigned"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasOrgContext])
def contact_assign_group(request, contact_id):
    """POST /talkhub/contacts/{id}/assign-group/."""
    ser = AssignGroupSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    contact, user_ns, err = _get_contact_with_subscriber(request, contact_id)
    if err:
        return err
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        client.assign_agent_group(user_ns, ser.validated_data["group_id"])
        return Response({"status": "group_assigned"})
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════
# MODULE 11 — Analytics
# ══════════════════════════════════════════════════════════════════════


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def analytics_flow_summary(request):
    """GET /talkhub/analytics/flow-summary/."""
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.get_flow_summary(**dict(request.query_params)))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def analytics_agent_summary(request):
    """GET /talkhub/analytics/agent-summary/."""
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.get_flow_agent_summary(**dict(request.query_params)))
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════
# MODULE 12 — Workspace / Flows
# ══════════════════════════════════════════════════════════════════════


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def workspace_info(request):
    """GET /talkhub/workspace/."""
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.get_team_info())
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def flows_list(request):
    """GET /talkhub/flows/."""
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.get_team_flows())
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasOrgContext])
def channels_list(request):
    """GET /talkhub/channels/ — workspace channels from Omni API."""
    client, err = _get_client_for_request(request)
    if err:
        return err
    try:
        return Response(client.get_channels())
    except TalkHubAPIError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
