"""
Celery tasks for the channels app.

- poll_imap_emails: Polls IMAP for new emails and creates conversations/messages.
"""

import email
import email.header
import email.utils
import imaplib
import logging
import re
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


def _decode_header(value):
    """Decode an email header value."""
    if not value:
        return ""
    decoded_parts = email.header.decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _get_email_body(msg):
    """Extract email body, preserving HTML when available."""
    if msg.is_multipart():
        text_body = ""
        html_body = ""
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/plain":
                    text_body = decoded
                elif content_type == "text/html":
                    html_body = decoded
            except Exception:
                continue
        # Return both: prefer HTML for rich rendering, text as fallback
        return {"text": text_body.strip(), "html": html_body.strip()}
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload is None:
                return {"text": "", "html": ""}
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace").strip()
            content_type = msg.get_content_type()
            if content_type == "text/html":
                return {"text": "", "html": decoded}
            return {"text": decoded, "html": ""}
        except Exception:
            return {"text": "", "html": ""}


def _extract_email_address(header_value):
    """Extract email address from header like 'Name <email@example.com>'."""
    if not header_value:
        return ""
    _, addr = email.utils.parseaddr(header_value)
    return addr.lower()


def _extract_name(header_value):
    """Extract name from header like 'Name <email@example.com>'."""
    if not header_value:
        return ""
    name, _ = email.utils.parseaddr(header_value)
    return name


def _get_imap_config(smtp_config):
    """Get IMAP config from SMTP integration config, with fallbacks."""
    imap_host = smtp_config.get("imap_host", "")
    if not imap_host:
        # Try to derive IMAP host from SMTP host
        smtp_host = smtp_config.get("smtp_host", "")
        if smtp_host:
            imap_host = smtp_host.replace("smtp.", "imap.")
        else:
            return None

    return {
        "host": imap_host,
        "port": int(smtp_config.get("imap_port", 993)),
        "user": smtp_config.get("imap_user", "") or smtp_config.get("smtp_user", ""),
        "password": smtp_config.get("imap_password", "") or smtp_config.get("smtp_password", ""),
    }


def _decrypt_smtp_config(config):
    """Decrypt secret fields in SMTP config."""
    from cryptography.fernet import Fernet, InvalidToken
    from django.conf import settings

    config = dict(config)
    fernet_key = getattr(settings, "FERNET_KEY", None)
    if fernet_key:
        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        for field in ("smtp_password", "imap_password"):
            value = config.get(field, "")
            if value and isinstance(value, str) and value.startswith("gAAAAA"):
                try:
                    config[field] = f.decrypt(value.encode()).decode()
                except (InvalidToken, Exception):
                    logger.error(
                        "Failed to decrypt %s — FERNET_KEY may be wrong or value corrupted", field
                    )
                    config[field] = ""  # Clear so credential check catches it
    return config


@shared_task(name="channels.tasks.poll_imap_emails")
def poll_imap_emails():
    """
    Poll IMAP for new emails for all orgs with active SMTP integration.

    Creates Conversation + Message records from incoming emails.
    Runs every 2 minutes via Celery Beat.

    IMPORTANT: Uses raw SQL to discover org IDs because the
    integration_connection table has FORCE ROW LEVEL SECURITY.
    Without explicit org context, ORM queries return 0 rows.
    The organization table has no RLS, so we iterate through all orgs
    and set RLS context for each before querying IntegrationConnection.
    """
    from django.core.cache import cache
    from django.db import connection as db_conn

    from integrations.models import IntegrationConnection

    # Prevent concurrent executions (lock for 5 minutes max)
    lock_key = "lock:poll_imap_emails"
    if not cache.add(lock_key, "1", timeout=300):
        logger.info("IMAP poll: skipping, another instance is running")
        return

    try:
        # Get all org IDs from organization table (no RLS on this table)
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT id FROM organization")
            org_ids = [row[0] for row in cursor.fetchall()]

        if not org_ids:
            logger.info("IMAP poll: no organizations found")
            return

        total_new = 0
        orgs_with_smtp = 0

        for org_id in org_ids:
            conn = None
            try:
                set_rls_context(str(org_id))

                conn = IntegrationConnection.objects.filter(
                    connector_slug="smtp", is_active=True, is_connected=True
                ).select_related("org").first()

                if not conn:
                    continue

                orgs_with_smtp += 1
                config = _decrypt_smtp_config(conn.config_json or {})
                imap_config = _get_imap_config(config)

                if not imap_config:
                    logger.warning("IMAP poll: no IMAP config for org %s, skipping", org_id)
                    conn.last_error = "IMAP não configurado (host ausente)"
                    conn.error_count = (conn.error_count or 0) + 1
                    conn.save(update_fields=["last_error", "error_count", "updated_at"])
                    continue

                if not imap_config.get("user") or not imap_config.get("password"):
                    logger.warning("IMAP poll: missing credentials for org %s (user=%s, pass_len=%d)",
                                   org_id, imap_config.get("user", ""), len(imap_config.get("password", "")))
                    conn.last_error = "Credenciais IMAP ausentes (usuário ou senha vazia após decriptação)"
                    conn.error_count = (conn.error_count or 0) + 1
                    conn.save(update_fields=["last_error", "error_count", "updated_at"])
                    continue

                logger.info("IMAP poll: connecting to %s:%s for org %s",
                            imap_config["host"], imap_config["port"], org_id)
                count = _poll_org_emails(conn.org, config, imap_config)
                total_new += count

                # Update connection status on success
                conn.last_sync_at = timezone.now()
                conn.error_count = 0
                conn.last_error = ""
                conn.health_status = "healthy"
                conn.save(update_fields=["last_sync_at", "error_count", "last_error", "health_status", "updated_at"])

                if count:
                    logger.info("IMAP poll: org %s — %d new email(s)", org_id, count)

            except Exception as exc:
                logger.error(
                    "IMAP poll failed for org %s: %s", org_id, exc, exc_info=True
                )
                # Update connection error status
                try:
                    if conn:
                        conn.error_count = (conn.error_count or 0) + 1
                        conn.last_error = str(exc)[:500]
                        conn.health_status = "degraded" if (conn.error_count or 0) <= 5 else "down"
                        conn.save(update_fields=["error_count", "last_error", "health_status", "updated_at"])
                except Exception:
                    pass

        logger.info("IMAP poll complete: %d org(s) with SMTP, %d new email(s)", orgs_with_smtp, total_new)
    finally:
        cache.delete(lock_key)


def _poll_org_emails(org, smtp_config, imap_config):
    """Poll IMAP for a single org. Returns count of new messages."""
    from channels.models import ChannelConfig
    from contacts.models import Contact
    from conversations.models import Conversation, Message

    host = imap_config["host"]
    port = imap_config["port"]
    user = imap_config["user"]
    password = imap_config["password"]

    if not user or not password:
        return 0

    our_email = smtp_config.get("from_email", user).lower()

    # Connect to IMAP
    if port == 993:
        imap = imaplib.IMAP4_SSL(host, port, timeout=30)
    else:
        imap = imaplib.IMAP4(host, port, timeout=30)
        imap.starttls()

    try:
        imap.login(user, password)
        imap.select("INBOX")

        # Search for emails from the last 3 days
        since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
        _, msg_nums = imap.search(None, f'(SINCE {since_date})')

        if not msg_nums or not msg_nums[0]:
            return 0

        msg_ids = msg_nums[0].split()
        count = 0

        for msg_id in msg_ids[-50:]:  # Process the most recent 50
            try:
                # Use BODY.PEEK[] to avoid marking messages as \Seen
                _, msg_data = imap.fetch(msg_id, "(BODY.PEEK[])")
                if not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                from_header = _decode_header(msg.get("From", ""))
                to_header = _decode_header(msg.get("To", ""))
                cc_header = _decode_header(msg.get("Cc", ""))
                date_header = msg.get("Date", "")
                from_email = _extract_email_address(from_header)
                from_name = _extract_name(from_header) or from_email.split("@")[0]
                subject = _decode_header(msg.get("Subject", ""))
                message_id = msg.get("Message-ID", "")
                in_reply_to = msg.get("In-Reply-To", "")
                references = msg.get("References", "")
                body_parts = _get_email_body(msg)
                text_body = body_parts.get("text", "")
                html_body = body_parts.get("html", "")

                # Parse email date
                email_date = None
                if date_header:
                    try:
                        parsed = email.utils.parsedate_to_datetime(date_header)
                        if parsed:
                            email_date = parsed
                    except Exception:
                        pass

                # Skip emails from ourselves
                if from_email == our_email:
                    continue

                # Skip empty emails
                if not text_body and not html_body and not subject:
                    continue

                # Find or create contact
                contact = Contact.objects.filter(
                    org=org, email__iexact=from_email
                ).first()
                if not contact:
                    name_parts = from_name.split(" ", 1)
                    contact = Contact.objects.create(
                        org=org,
                        first_name=name_parts[0][:255],
                        last_name=name_parts[1][:255] if len(name_parts) > 1 else "",
                        email=from_email[:255],
                    )

                # Find existing conversation by threading or contact
                # Use atomic block to prevent race condition on creation
                from django.db import transaction

                conversation = None
                if in_reply_to or references:
                    # Try to match by email thread
                    ref_ids = (references or "").split() + ([in_reply_to] if in_reply_to else [])
                    for ref_id in ref_ids:
                        conversation = Conversation.objects.filter(
                            org=org,
                            channel="smtp_native",
                            messages__metadata_json__email_message_id=ref_id,
                        ).first()
                        if conversation:
                            break

                if not conversation:
                    # Find open conversation with same contact on email channel
                    conversation = Conversation.objects.filter(
                        org=org,
                        contact=contact,
                        channel="smtp_native",
                        status__in=["open", "pending"],
                    ).order_by("-last_message_at").first()

                if not conversation:
                    # Atomic get_or_create to prevent duplicate conversations
                    with transaction.atomic():
                        conversation, _ = Conversation.objects.get_or_create(
                            org=org,
                            contact=contact,
                            channel="smtp_native",
                            status="open",
                            defaults={"metadata_json": {"email_subject": subject}},
                        )

                # Check for duplicate message (dedup by message_id)
                if message_id:
                    exists = Message.objects.filter(
                        org=org,
                        metadata_json__email_message_id=message_id,
                    ).exists()
                    if exists:
                        continue

                # Create message with HTML body preserved
                timestamp = email_date if email_date and timezone.is_aware(email_date) else (
                    timezone.make_aware(email_date) if email_date else timezone.now()
                )

                # Content: prefer HTML for rich rendering, fallback to text
                msg_content = html_body if html_body else text_body

                Message.objects.create(
                    org=org,
                    conversation=conversation,
                    direction="in",
                    msg_type="text",
                    content=msg_content,
                    sender_name=from_name,
                    sender_id=from_email,
                    timestamp=timestamp,
                    metadata_json={
                        "email_subject": subject,
                        "email_from": from_email,
                        "email_from_name": from_name,
                        "email_to": to_header,
                        "email_cc": cc_header,
                        "email_date": date_header,
                        "email_message_id": message_id,
                        "email_in_reply_to": in_reply_to,
                        "email_references": references,
                        "content_type": "html" if html_body else "text",
                    },
                )

                conversation.last_message_at = timestamp
                conversation.status = "open"
                conversation.save(update_fields=["last_message_at", "status", "updated_at"])

                count += 1

            except Exception as exc:
                logger.error("Failed to process email %s: %s", msg_id, exc)
                continue

        return count

    finally:
        try:
            imap.close()
            imap.logout()
        except Exception:
            pass
