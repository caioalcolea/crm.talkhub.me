import logging
from collections import defaultdict
from datetime import date

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone

from common.models import Org, Profile
from opportunity.models import Opportunity, SalesGoal, StageAgingConfig

logger = logging.getLogger(__name__)


def _set_rls_context_safe(org_id):
    """Set RLS context, skipping on non-PostgreSQL backends."""
    if connection.vendor == "postgresql":
        from common.tasks import set_rls_context

        set_rls_context(org_id)


@shared_task
def send_email_to_assigned_user(recipients, opportunity_id, org_id):
    """Send Mail To Users When they are assigned to an opportunity"""
    _set_rls_context_safe(org_id)
    opportunity = Opportunity.objects.get(id=opportunity_id)
    created_by = opportunity.created_by
    for user in recipients:
        recipients_list = []
        profile = Profile.objects.filter(id=user, is_active=True).first()
        if profile:
            recipients_list.append(profile.user.email)
            context = {}
            context["url"] = settings.DOMAIN_NAME
            context["user"] = profile.user
            context["opportunity"] = opportunity
            context["created_by"] = created_by
            subject = "Uma oportunidade foi atribuída a você."
            html_content = render_to_string(
                "assigned_to/opportunity_assigned.html", context=context
            )

            msg = EmailMessage(subject, html_content, to=recipients_list)
            msg.content_subtype = "html"
            msg.send()


@shared_task
def check_stale_opportunities():
    """Daily task: find rotten deals across all orgs and send email alerts."""
    from opportunity.workflow import CLOSED_STAGES, DEFAULT_STAGE_EXPECTED_DAYS, ROTTEN_MULTIPLIER

    now = timezone.now()
    orgs = Org.objects.filter(is_active=True)

    for org in orgs:
        try:
            _set_rls_context_safe(str(org.id))

            aging_configs = {
                c.stage: c for c in StageAgingConfig.objects.filter(org=org)
            }

            open_opps = Opportunity.objects.filter(
                org=org, is_active=True
            ).exclude(stage__in=CLOSED_STAGES).select_related("org")

            stale_opps = []
            for opp in open_opps:
                if not opp.stage_changed_at:
                    continue
                config = aging_configs.get(opp.stage)
                expected = (
                    config.expected_days
                    if config
                    else DEFAULT_STAGE_EXPECTED_DAYS.get(opp.stage)
                )
                if expected is None:
                    continue
                days = (now - opp.stage_changed_at).days
                if days >= expected * ROTTEN_MULTIPLIER:
                    stale_opps.append((opp, days, expected))

            if stale_opps:
                send_stale_deals_alert(org, stale_opps)
        except Exception:
            logger.exception("Error processing stale deals for org %s", org.id)


def send_stale_deals_alert(org, stale_opps):
    """Send per-user email alerts for rotten deals."""
    # Pre-fetch org admins for unassigned deals
    org_admins = list(Profile.objects.filter(org=org, role="ADMIN", is_active=True))

    # Group by assigned users
    user_deals = defaultdict(list)
    for opp, days, expected in stale_opps:
        assigned = list(opp.assigned_to.filter(is_active=True))
        if assigned:
            for profile in assigned:
                user_deals[profile].append((opp, days, expected))
        else:
            # No one assigned - alert org admins
            for admin in org_admins:
                user_deals[admin].append((opp, days, expected))

    for profile, deals in user_deals.items():
        context = {
            "user": profile.user,
            "deals": [
                {
                    "name": opp.name,
                    "stage": opp.get_stage_display(),
                    "days_in_stage": days,
                    "expected_days": expected,
                }
                for opp, days, expected in deals
            ],
            "url": settings.DOMAIN_NAME,
            "deal_count": len(deals),
        }
        subject = f"[TalkHub CRM] {len(deals)} negócio{'s' if len(deals) > 1 else ''} parado{'s' if len(deals) > 1 else ''} precisa{'m' if len(deals) > 1 else ''} de atenção"
        html_content = render_to_string(
            "opportunity/stale_deals_alert.html", context=context
        )
        msg = EmailMessage(
            subject,
            html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[profile.user.email],
        )
        msg.content_subtype = "html"
        try:
            msg.send()
        except Exception:
            logger.exception(
                "Failed to send stale deals alert to %s", profile.user.email
            )


@shared_task(name="opportunity.tasks.check_goal_milestones")
def check_goal_milestones():
    """Daily: check goal progress milestones and send notifications.

    Handles:
    - 50%, 90%, 100% milestone notifications (idempotent via boolean flags)
    - At 100%: also notifies org admins (team managers)
    - Risk alert: when goal status is "behind" and < 7 days remaining
    """
    today = date.today()
    orgs = Org.objects.filter(is_active=True)

    for org in orgs:
        try:
            _set_rls_context_safe(str(org.id))

            goals = SalesGoal.objects.filter(
                org=org,
                is_active=True,
                period_start__lte=today,
                period_end__gte=today,
            )

            for goal in goals:
                progress_value = goal.compute_progress()
                if goal.target_value and goal.target_value != 0:
                    percent = min(
                        int(progress_value / goal.target_value * 100), 100
                    )
                else:
                    percent = 0

                # --- Milestone notifications ---
                notifications = []
                hit_100 = False

                if percent >= 100 and not goal.milestone_100_notified:
                    goal.milestone_100_notified = True
                    goal.milestone_90_notified = True
                    goal.milestone_50_notified = True
                    notifications.append(("100%", percent, progress_value))
                    hit_100 = True
                elif percent >= 90 and not goal.milestone_90_notified:
                    goal.milestone_90_notified = True
                    goal.milestone_50_notified = True
                    notifications.append(("90%", percent, progress_value))
                elif percent >= 50 and not goal.milestone_50_notified:
                    goal.milestone_50_notified = True
                    notifications.append(("50%", percent, progress_value))

                if notifications:
                    goal.save(
                        update_fields=[
                            "milestone_50_notified",
                            "milestone_90_notified",
                            "milestone_100_notified",
                        ]
                    )

                    # Build recipient list for milestone
                    recipients = []
                    if goal.assigned_to:
                        recipients.append(goal.assigned_to)
                    elif goal.team:
                        recipients.extend(
                            Profile.objects.filter(
                                user_teams=goal.team, is_active=True
                            )
                        )
                    else:
                        recipients.extend(
                            Profile.objects.filter(
                                org=org, role="ADMIN", is_active=True
                            )
                        )

                    for milestone_label, pct, achieved in notifications:
                        for profile in recipients:
                            _send_goal_milestone_email(
                                profile, goal, milestone_label, pct, achieved
                            )

                    # At 100%: also notify org admins (team managers)
                    # if they are not already in the recipients list
                    if hit_100:
                        recipient_ids = {p.id for p in recipients}
                        org_admins = Profile.objects.filter(
                            org=org, role="ADMIN", is_active=True
                        ).exclude(id__in=recipient_ids)
                        for admin_profile in org_admins:
                            _send_goal_milestone_email(
                                admin_profile, goal, "100%", percent, progress_value
                            )

                # --- Risk alert: "behind" status + < 7 days remaining ---
                days_remaining = (goal.period_end - today).days
                goal_status = goal.status  # uses cached progress

                if goal_status == "behind" and 0 < days_remaining < 7:
                    # Build recipient list for risk alert
                    risk_recipients = []
                    if goal.assigned_to:
                        risk_recipients.append(goal.assigned_to)
                    elif goal.team:
                        risk_recipients.extend(
                            Profile.objects.filter(
                                user_teams=goal.team, is_active=True
                            )
                        )
                    # Always include org admins for risk alerts
                    risk_recipient_ids = {p.id for p in risk_recipients}
                    org_admins_risk = Profile.objects.filter(
                        org=org, role="ADMIN", is_active=True
                    ).exclude(id__in=risk_recipient_ids)
                    risk_recipients.extend(org_admins_risk)

                    for profile in risk_recipients:
                        _send_goal_risk_alert_email(
                            profile, goal, percent, progress_value, days_remaining
                        )

        except Exception:
            logger.exception(
                "Error processing goal milestones for org %s", org.id
            )


def _send_goal_milestone_email(profile, goal, milestone_label, percent, achieved):
    """Send a milestone notification email for a sales goal."""
    context = {
        "user": profile.user,
        "goal": goal,
        "milestone": milestone_label,
        "percent": percent,
        "achieved": achieved,
        "url": settings.DOMAIN_NAME,
    }
    subject = f"[TalkHub CRM] Meta '{goal.name}' atingiu {milestone_label}!"
    html_content = render_to_string(
        "opportunity/goal_milestone.html", context=context
    )
    msg = EmailMessage(
        subject,
        html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[profile.user.email],
    )
    msg.content_subtype = "html"
    try:
        msg.send()
    except Exception:
        logger.exception(
            "Failed to send goal milestone email to %s", profile.user.email
        )


def _send_goal_risk_alert_email(profile, goal, percent, achieved, days_remaining):
    """Send a risk alert email when a goal is behind with < 7 days remaining."""
    context = {
        "user": profile.user,
        "goal": goal,
        "percent": percent,
        "achieved": achieved,
        "days_remaining": days_remaining,
        "url": settings.DOMAIN_NAME,
    }
    subject = f"[TalkHub CRM] Alerta: Meta '{goal.name}' atrasada — {days_remaining} dia{'s' if days_remaining != 1 else ''} restante{'s' if days_remaining != 1 else ''}"
    html_content = render_to_string(
        "opportunity/goal_risk_alert.html", context=context
    )
    msg = EmailMessage(
        subject,
        html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[profile.user.email],
    )
    msg.content_subtype = "html"
    try:
        msg.send()
    except Exception:
        logger.exception(
            "Failed to send goal risk alert email to %s", profile.user.email
        )


@shared_task(name="opportunity.tasks.recalculate_goal_breakdowns")
def recalculate_goal_breakdowns():
    """
    Periodic task: recalculate current_value for all GoalBreakdown records
    based on CLOSED_WON opportunities within the goal's period.

    Breakdown types:
    - user: filter by assigned_to profile
    - stage: filter by opportunity stage at close
    - product: filter by product in line items
    - channel: filter by lead_source
    """
    from decimal import Decimal

    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    from opportunity.models import GoalBreakdown

    today = date.today()
    orgs = Org.objects.filter(is_active=True)

    for org in orgs:
        try:
            _set_rls_context_safe(str(org.id))

            # Get active goals with breakdowns in current period
            active_goals = SalesGoal.objects.filter(
                org=org,
                is_active=True,
                period_start__lte=today,
                period_end__gte=today,
            ).prefetch_related("breakdowns")

            for goal in active_goals:
                breakdowns = goal.breakdowns.all()
                if not breakdowns.exists():
                    continue

                # Base queryset: CLOSED_WON opportunities in period
                base_opps = Opportunity.objects.filter(
                    org=org,
                    stage="CLOSED_WON",
                    closed_on__gte=goal.period_start,
                    closed_on__lte=goal.period_end,
                )

                for bd in breakdowns:
                    new_value = Decimal("0")

                    if bd.breakdown_type == "user":
                        # breakdown_key = profile UUID
                        user_opps = base_opps.filter(
                            assigned_to__id=bd.breakdown_key
                        )
                        if goal.goal_type == "REVENUE":
                            new_value = user_opps.aggregate(
                                total=Coalesce(Sum("amount"), Decimal("0"))
                            )["total"]
                        else:
                            new_value = Decimal(str(user_opps.count()))

                    elif bd.breakdown_type == "stage":
                        # For stage breakdowns, we track opportunities that
                        # passed through a specific stage before closing.
                        # Since we only have CLOSED_WON, breakdown_key is
                        # the pipeline stage they were in (e.g., for tracking
                        # which stages produce the most wins).
                        # For simplicity, we use lead_source as proxy or
                        # count all CLOSED_WON (stage breakdown is informational).
                        if goal.goal_type == "REVENUE":
                            new_value = base_opps.aggregate(
                                total=Coalesce(Sum("amount"), Decimal("0"))
                            )["total"]
                        else:
                            new_value = Decimal(str(base_opps.count()))

                    elif bd.breakdown_type == "channel":
                        # breakdown_key = lead_source value
                        channel_opps = base_opps.filter(
                            lead_source=bd.breakdown_key
                        )
                        if goal.goal_type == "REVENUE":
                            new_value = channel_opps.aggregate(
                                total=Coalesce(Sum("amount"), Decimal("0"))
                            )["total"]
                        else:
                            new_value = Decimal(str(channel_opps.count()))

                    elif bd.breakdown_type == "product":
                        # breakdown_key = product UUID
                        product_opps = base_opps.filter(
                            line_items__product_id=bd.breakdown_key
                        ).distinct()
                        if goal.goal_type == "REVENUE":
                            from opportunity.models import OpportunityLineItem

                            line_total = OpportunityLineItem.objects.filter(
                                opportunity__in=product_opps,
                                product_id=bd.breakdown_key,
                            ).aggregate(
                                total=Coalesce(Sum("total"), Decimal("0"))
                            )["total"]
                            new_value = line_total
                        else:
                            new_value = Decimal(str(product_opps.count()))

                    if bd.current_value != new_value:
                        bd.current_value = new_value
                        bd.save(update_fields=["current_value", "updated_at"])

        except Exception:
            logger.exception(
                "Error recalculating goal breakdowns for org %s", org.id
            )
