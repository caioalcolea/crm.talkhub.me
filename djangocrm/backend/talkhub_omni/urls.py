"""
TalkHub Omni URL configuration — refatorado v2.
"""

from django.urls import path

from . import views

app_name = "talkhub_omni"

urlpatterns = [
    # ── Module 1: Connection ──────────────────────────────────────────
    path("status/", views.talkhub_status, name="status"),
    path("credentials/", views.talkhub_credentials, name="credentials"),
    path("connect/", views.talkhub_connect, name="connect"),
    path("disconnect/", views.talkhub_disconnect, name="disconnect"),

    # ── Module 2: Channel Config ──────────────────────────────────────
    path("channel-config/", views.channel_config_list, name="channel-config-list"),
    path("channel-config/<uuid:channel_id>/", views.channel_config_detail, name="channel-config-detail"),
    path("channel-config/<uuid:channel_id>/test/", views.channel_test, name="channel-test"),

    # ── Module 3: Sync Config ─────────────────────────────────────────
    path("sync/config/", views.sync_config, name="sync-config"),
    path("sync/now/", views.sync_now, name="sync-now"),
    path("sync/history/", views.sync_history, name="sync-history"),
    path("sync/jobs/<uuid:job_id>/", views.sync_job_status, name="sync-job-status"),

    # ── Module 4: Contact Sync ────────────────────────────────────────
    path("sync/contacts/", views.sync_contacts_start, name="sync-contacts"),
    path("contacts/<uuid:contact_id>/push/", views.contact_push, name="contact-push"),
    path("contacts/<uuid:contact_id>/chat-history/", views.contact_chat_history, name="contact-chat-history"),

    # ── Module 5: Messaging ───────────────────────────────────────────
    path("contacts/<uuid:contact_id>/send/text/", views.send_text, name="send-text"),
    path("contacts/<uuid:contact_id>/send/sms/", views.send_sms, name="send-sms"),
    path("contacts/<uuid:contact_id>/send/email/", views.send_email, name="send-email"),
    path("contacts/<uuid:contact_id>/send/content/", views.send_content, name="send-content"),
    path("contacts/<uuid:contact_id>/send/whatsapp-template/", views.send_whatsapp_template, name="send-wa-template"),
    path("contacts/<uuid:contact_id>/send/flow/", views.send_flow, name="send-flow"),
    path("send/broadcast/", views.send_broadcast, name="send-broadcast"),
    path("whatsapp-templates/", views.whatsapp_templates, name="whatsapp-templates"),

    # ── Module 6: Opt-in / Opt-out ────────────────────────────────────
    path("contacts/<uuid:contact_id>/opt/", views.opt_in_out, name="opt-in-out"),

    # ── Module 7: Tags & Labels ───────────────────────────────────────
    path("contacts/<uuid:contact_id>/tags/add/", views.contact_tags_add, name="contact-tags-add"),
    path("contacts/<uuid:contact_id>/tags/remove/", views.contact_tags_remove, name="contact-tags-remove"),
    path("contacts/<uuid:contact_id>/labels/add/", views.contact_labels_add, name="contact-labels-add"),
    path("contacts/<uuid:contact_id>/labels/remove/", views.contact_labels_remove, name="contact-labels-remove"),

    # ── Module 8: Tickets ─────────────────────────────────────────────
    path("sync/tickets/", views.sync_tickets_start, name="sync-tickets"),
    path("ticket-list-mappings/", views.ticket_list_mappings, name="ticket-list-mappings"),

    # ── Module 9: Team Members ────────────────────────────────────────
    path("team-members/", views.team_members_list, name="team-members"),

    # ── Module 10: Bot Control ────────────────────────────────────────
    path("contacts/<uuid:contact_id>/pause-bot/", views.contact_pause_bot, name="contact-pause-bot"),
    path("contacts/<uuid:contact_id>/resume-bot/", views.contact_resume_bot, name="contact-resume-bot"),
    path("contacts/<uuid:contact_id>/log-event/", views.contact_log_event, name="contact-log-event"),
    path("contacts/<uuid:contact_id>/user-fields/", views.contact_user_fields, name="contact-user-fields"),
    path("contacts/<uuid:contact_id>/assign-agent/", views.contact_assign_agent, name="contact-assign-agent"),
    path("contacts/<uuid:contact_id>/unassign-agent/", views.contact_unassign_agent, name="contact-unassign-agent"),
    path("contacts/<uuid:contact_id>/assign-group/", views.contact_assign_group, name="contact-assign-group"),

    # ── Module 11: Analytics ──────────────────────────────────────────
    path("analytics/flow-summary/", views.analytics_flow_summary, name="analytics-flow-summary"),
    path("analytics/agent-summary/", views.analytics_agent_summary, name="analytics-agent-summary"),

    # ── Module 12: Workspace / Flows ──────────────────────────────────
    path("workspace/", views.workspace_info, name="workspace"),
    path("flows/", views.flows_list, name="flows"),
    path("channels/", views.channels_list, name="channels"),
]
