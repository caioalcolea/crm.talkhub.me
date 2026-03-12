import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import ValidationError, validate_email
from django.db import connection
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(name="cowork.tasks.send_cowork_invite_email")
def send_cowork_invite_email(invite_id):
    """Send email invitation for a cowork room guest."""
    # Raw SQL to bypass RLS (same pattern as CoworkGuestJoinView)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ci.guest_name, ci.guest_email, ci.token, ci.expires_at,
                   cr.name as room_name
            FROM cowork_coworkinvite ci
            JOIN cowork_coworkroom cr ON cr.id = ci.room_id
            WHERE ci.id = %s
            LIMIT 1
            """,
            [invite_id],
        )
        row = cursor.fetchone()

    if not row:
        logger.warning("CoworkInvite not found: %s", invite_id)
        return

    guest_name, guest_email, token, expires_at, room_name = row

    if not guest_email:
        logger.info("No email for cowork invite %s, skipping", invite_id)
        return

    email = guest_email.strip()
    try:
        validate_email(email)
    except ValidationError:
        logger.warning("Cowork invite email skipped: invalid email %s", email)
        return

    join_url = f"{settings.DOMAIN_NAME}/cowork/{token}"

    html_content = render_to_string(
        "cowork/invite_email.html",
        {
            "join_url": join_url,
            "guest_name": guest_name,
            "room_name": room_name,
        },
    )

    subject = f"Convite para Sala Cowork: {room_name} — TalkHub CRM"
    msg = EmailMessage(
        subject,
        html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.content_subtype = "html"
    try:
        msg.send()
        logger.info("Cowork invite email sent to %s for room %s", email, room_name)
    except Exception:
        logger.exception("Failed to send cowork invite email to %s", email)
