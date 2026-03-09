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
    """Extract plain text body from email message."""
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
        # Prefer plain text, fallback to HTML stripped of tags
        if text_body:
            return text_body.strip()
        if html_body:
            clean = re.sub(r"<[^>]+>", "", html_body)
            return re.sub(r"\s+", " ", clean).strip()
        return ""
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload is None:
                return ""
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace").strip()
        except Exception:
            return ""


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
                    pass
    return config


@shared_task(name="channels.tasks.poll_imap_emails")
def poll_imap_emails():
    """
    Poll IMAP for new emails for all orgs with active SMTP integration.

    Creates Conversation + Message records from incoming emails.
    Runs every 2 minutes via Celery Beat.
    """
    from integrations.models import IntegrationConnection

    connections = IntegrationConnection.objects.filter(
        connector_slug="smtp", is_active=True, is_connected=True
    )

    total_new = 0
    for conn in connections:
        try:
            set_rls_context(str(conn.org_id))
            config = _decrypt_smtp_config(conn.config_json or {})
            imap_config = _get_imap_config(config)
            if not imap_config:
                continue

            count = _poll_org_emails(conn.org, config, imap_config)
            total_new += count
        except Exception as exc:
            logger.error(
                "IMAP poll failed for org %s: %s", conn.org_id, exc
            )

    if total_new:
        logger.info("IMAP poll: %d new emails processed", total_new)


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

        # Search for UNSEEN emails from the last 3 days (safety window)
        since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
        _, msg_nums = imap.search(None, f'(UNSEEN SINCE {since_date})')

        if not msg_nums or not msg_nums[0]:
            return 0

        msg_ids = msg_nums[0].split()
        count = 0

        for msg_id in msg_ids[:50]:  # Process max 50 per poll
            try:
                _, msg_data = imap.fetch(msg_id, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                from_header = _decode_header(msg.get("From", ""))
                from_email = _extract_email_address(from_header)
                from_name = _extract_name(from_header) or from_email.split("@")[0]
                subject = _decode_header(msg.get("Subject", ""))
                message_id = msg.get("Message-ID", "")
                in_reply_to = msg.get("In-Reply-To", "")
                references = msg.get("References", "")
                body = _get_email_body(msg)

                # Skip emails from ourselves
                if from_email == our_email:
                    continue

                # Skip empty emails
                if not body and not subject:
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
                    conversation = Conversation.objects.create(
                        org=org,
                        contact=contact,
                        channel="smtp_native",
                        status="open",
                        metadata_json={"email_subject": subject},
                    )

                # Check for duplicate message
                if message_id:
                    exists = Message.objects.filter(
                        org=org,
                        conversation=conversation,
                        metadata_json__email_message_id=message_id,
                    ).exists()
                    if exists:
                        continue

                # Create message
                now = timezone.now()
                msg_content = body
                if subject:
                    msg_content = f"**{subject}**\n\n{body}"

                Message.objects.create(
                    org=org,
                    conversation=conversation,
                    direction="in",
                    msg_type="text",
                    content=msg_content,
                    sender_name=from_name,
                    sender_id=from_email,
                    timestamp=now,
                    metadata_json={
                        "email_subject": subject,
                        "email_from": from_email,
                        "email_message_id": message_id,
                        "email_in_reply_to": in_reply_to,
                        "email_references": references,
                    },
                )

                conversation.last_message_at = now
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
