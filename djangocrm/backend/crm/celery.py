from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.dev_settings')
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.server_settings')

app = Celery("crm")

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
app.autodiscover_tasks(related_name="celery_tasks")  # tasks app uses celery_tasks.py

# Celery Beat Schedule for recurring tasks
app.conf.beat_schedule = {
    # Generate invoices from recurring invoice templates - daily at midnight
    "generate-recurring-invoices": {
        "task": "invoices.tasks.generate_recurring_invoices",
        "schedule": crontab(hour=0, minute=0),
    },
    # Mark overdue invoices - daily at 1 AM
    "check-overdue-invoices": {
        "task": "invoices.tasks.check_overdue_invoices",
        "schedule": crontab(hour=1, minute=0),
    },
    # Process payment reminders - daily at 9 AM
    "process-payment-reminders": {
        "task": "invoices.tasks.process_payment_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    # Mark expired estimates - daily at midnight
    "check-expired-estimates": {
        "task": "invoices.tasks.check_expired_estimates",
        "schedule": crontab(hour=0, minute=30),
    },
    # Check for stale/rotten opportunities - daily at 8 AM
    "check-stale-opportunities": {
        "task": "opportunity.tasks.check_stale_opportunities",
        "schedule": crontab(hour=8, minute=0),
    },
    # Check goal milestones and send notifications - daily at 9:15 AM
    "check-goal-milestones": {
        "task": "opportunity.tasks.check_goal_milestones",
        "schedule": crontab(hour=9, minute=15),
    },
    # Cases — SLA breach check every 15 minutes
    "cases-sla-check": {
        "task": "cases.tasks.check_sla_breaches",
        "schedule": crontab(minute="*/15"),
    },
    # TalkHub Omni — Sync contacts every 5 minutes
    "talkhub-sync-contacts": {
        "task": "talkhub_omni.tasks.periodic_sync_contacts",
        "schedule": crontab(minute="*/5"),
    },
    # TalkHub Omni — Sync tickets every 10 minutes
    "talkhub-sync-tickets": {
        "task": "talkhub_omni.tasks.periodic_sync_tickets",
        "schedule": crontab(minute="*/10"),
    },
    # TalkHub Omni — Sync ticket list structure 1x/dia às 2h
    "talkhub-sync-ticket-structure": {
        "task": "talkhub_omni.tasks.periodic_sync_ticket_structure",
        "schedule": crontab(hour=2, minute=0),
    },
    # TalkHub Omni — Sync tags 1x/dia às 3h
    "talkhub-sync-tags": {
        "task": "talkhub_omni.tasks.periodic_sync_tags",
        "schedule": crontab(hour=3, minute=0),
    },
    # TalkHub Omni — Sync team members 1x/dia às 4h
    "talkhub-sync-team-members": {
        "task": "talkhub_omni.tasks.periodic_sync_team_members",
        "schedule": crontab(hour=4, minute=0),
    },
    # TalkHub Omni — Sync statistics a cada hora
    "talkhub-sync-statistics": {
        "task": "talkhub_omni.tasks.periodic_sync_statistics",
        "schedule": crontab(minute=0),
    },
    # TalkHub Omni — Cleanup old logs 1x/dia às 5h
    "talkhub-cleanup-old-logs": {
        "task": "talkhub_omni.tasks.periodic_cleanup_old_logs",
        "schedule": crontab(hour=5, minute=0),
    },
    # Integrations — Cleanup old integration logs 1x/dia às 5:30h
    "integrations-cleanup-old-logs": {
        "task": "integrations.tasks.cleanup_old_logs",
        "schedule": crontab(hour=5, minute=30),
    },
    # Integrations — Health check every 10 minutes
    "integrations-health-check": {
        "task": "integrations.tasks.check_integration_health",
        "schedule": crontab(minute="*/10"),
    },
    # Integrations — Check pending syncs every 5 minutes
    "integrations-check-pending-syncs": {
        "task": "integrations.tasks.check_pending_syncs",
        "schedule": crontab(minute="*/5"),
    },
    # Integrations — Review agent (integrity check) 1x/dia às 6h
    "integrations-review-agent": {
        "task": "integrations.tasks.periodic_review_integrations",
        "schedule": crontab(hour=6, minute=0),
    },
    # Financeiro — Check overdue parcelas daily at 1:30 AM
    "check-overdue-parcelas": {
        "task": "financeiro.tasks.check_overdue_parcelas",
        "schedule": crontab(hour=1, minute=30),
    },
    # Invitations — Expire pending invitations daily at 2:30 AM
    "expire-pending-invitations": {
        "task": "common.tasks.expire_pending_invitations",
        "schedule": crontab(hour=2, minute=30),
    },
    # Automations — Process due routines every minute
    "automations-process-due-routines": {
        "task": "automations.tasks.process_due_routines",
        "schedule": crontab(minute="*"),
    },
    # Goals — Recalculate goal breakdowns every 30 minutes
    "recalculate-goal-breakdowns": {
        "task": "opportunity.tasks.recalculate_goal_breakdowns",
        "schedule": crontab(minute="*/30"),
    },
    # PIX — Expire pending transactions every 15 minutes
    "reconcile-pix-transactions": {
        "task": "financeiro.tasks.reconcile_pix_transactions",
        "schedule": crontab(minute="*/15"),
    },
    # PIX — Daily reconciliation report at 7 AM
    "pix-reconciliation-report": {
        "task": "financeiro.tasks.pix_reconciliation_report",
        "schedule": crontab(hour=7, minute=0),
    },
    # Campaigns — Check scheduled campaigns every minute
    "campaigns-check-scheduled": {
        "task": "campaigns.tasks.check_scheduled_campaigns",
        "schedule": crontab(minute="*"),
    },
    # Channels — Poll IMAP for new emails every 2 minutes
    "channels-poll-imap-emails": {
        "task": "channels.tasks.poll_imap_emails",
        "schedule": crontab(minute="*/2"),
    },
}
