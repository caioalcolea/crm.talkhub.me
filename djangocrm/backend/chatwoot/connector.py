"""
ChatwootConnector — BaseConnector implementation for Chatwoot live chat.

Registrado automaticamente via AppConfig.connector_class para aparecer
no Hub de Integrações (/settings/integrations).

Conecta o CRM ao Chatwoot para receber conversas omnichannel
(WhatsApp, Instagram, Web Chat, etc.) na caixa de entrada do CRM.
"""

import hashlib
import hmac
import logging
from typing import Any

import requests
from django.utils import timezone

from integrations.base import BaseConnector

logger = logging.getLogger(__name__)

WEBHOOK_EVENTS = [
    "message_created",
    "message_updated",
    "conversation_created",
    "conversation_updated",
    "conversation_status_changed",
    "contact_created",
    "contact_updated",
]


def _decrypt_config(config: dict) -> dict:
    """Decrypt secret fields from IntegrationConnection config."""
    from cryptography.fernet import Fernet, InvalidToken
    from django.conf import settings

    fernet_key = getattr(settings, "FERNET_KEY", None)
    if not fernet_key:
        return config

    f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
    decrypted = dict(config)
    for field in ("api_access_token", "webhook_secret"):
        value = decrypted.get(field, "")
        if value and isinstance(value, str) and value.startswith("gAAAAA"):
            try:
                decrypted[field] = f.decrypt(value.encode()).decode()
            except (InvalidToken, Exception):
                logger.error("Failed to decrypt %s", field)
    return decrypted


def _get_connection(org):
    """Get the active Chatwoot IntegrationConnection for an org."""
    from integrations.models import IntegrationConnection

    return IntegrationConnection.objects.filter(
        org=org, connector_slug="chatwoot", is_active=True, is_connected=True,
    ).first()


def _api_request(config, method, path, **kwargs):
    """Make an authenticated request to the Chatwoot API."""
    base_url = config["chatwoot_url"].rstrip("/")
    account_id = config["account_id"]
    token = config["api_access_token"]

    url = f"{base_url}/api/v1/accounts/{account_id}{path}"
    headers = {
        "api_access_token": token,
        "Content-Type": "application/json",
    }
    kwargs.setdefault("timeout", 30)
    merged_headers = {**headers, **kwargs.pop("headers", {})}
    kwargs["headers"] = merged_headers

    response = requests.request(method, url, **kwargs)
    return response


class ChatwootConnector(BaseConnector):
    slug = "chatwoot"
    name = "Chatwoot"
    icon = "message-circle"
    version = "1.0.0"

    def connect(self, org, config: dict) -> bool:
        """Validate Chatwoot credentials by listing agents."""
        chatwoot_url = config.get("chatwoot_url", "").rstrip("/")
        token = config.get("api_access_token", "")
        account_id = config.get("account_id")

        if not chatwoot_url or not token or not account_id:
            raise ValueError("URL do Chatwoot, Token de API e ID da Conta são obrigatórios.")

        try:
            resp = _api_request(config, "GET", "/agents")
            if resp.status_code == 401:
                raise ValueError("Token de API inválido. Verifique o api_access_token.")
            if resp.status_code == 403:
                raise ValueError("Sem permissão. Verifique as permissões do token.")
            resp.raise_for_status()
        except requests.ConnectionError:
            raise ValueError(f"Não foi possível conectar ao Chatwoot em {chatwoot_url}.")
        except requests.Timeout:
            raise ValueError(f"Timeout ao conectar ao Chatwoot em {chatwoot_url}.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Erro ao conectar ao Chatwoot: {exc}")

        logger.info("Chatwoot connect SUCCESS for org %s (account_id=%s)", org.id, account_id)

        # Auto-create ChannelConfig for the conversations system
        from channels.models import ChannelConfig
        ChannelConfig.objects.update_or_create(
            org=org,
            channel_type="chatwoot",
            defaults={
                "provider": "chatwoot",
                "display_name": "Chatwoot",
                "is_active": True,
                "config_json": {"account_id": config.get("account_id")},
                "capabilities_json": ["text", "image", "file"],
            },
        )
        logger.info("ChannelConfig for chatwoot created/updated for org %s", org.id)

        return True

    def post_connect(self, org, connection):
        """Register webhook after IntegrationConnection is saved (has token)."""
        config = _decrypt_config(connection.config_json or {})
        self._register_webhook(config, org, connection)

    def _register_webhook(self, config, org, connection=None):
        """Register a webhook in Chatwoot to receive events."""
        from django.conf import settings as django_settings

        domain = getattr(django_settings, "DOMAIN_NAME", "https://crm.talkhub.me")

        # Use token-based URL if connection has a webhook_token
        if connection and getattr(connection, "webhook_token", ""):
            webhook_url = f"{domain}/api/integrations/webhooks/chatwoot/{connection.webhook_token}/"
        else:
            webhook_url = f"{domain}/api/integrations/webhooks/chatwoot/"

        try:
            # List existing webhooks to avoid duplicates
            resp = _api_request(config, "GET", "/webhooks")
            if resp.status_code == 200:
                existing = resp.json().get("payload", resp.json() if isinstance(resp.json(), list) else [])
                for wh in existing:
                    if wh.get("url") == webhook_url:
                        logger.info("Chatwoot webhook already registered (id=%s)", wh.get("id"))
                        return wh.get("id")

            # Register new webhook
            resp = _api_request(config, "POST", "/webhooks", json={
                "webhook": {
                    "url": webhook_url,
                    "subscriptions": WEBHOOK_EVENTS,
                },
            })
            if resp.status_code in (200, 201):
                data = resp.json().get("payload", resp.json())
                webhook_id = data.get("id")
                logger.info("Chatwoot webhook registered (id=%s) for org %s", webhook_id, org.id)
                return webhook_id
            else:
                logger.warning(
                    "Failed to register Chatwoot webhook: %s %s", resp.status_code, resp.text[:200]
                )
        except Exception as exc:
            logger.warning("Could not auto-register Chatwoot webhook: %s", exc)

        return None

    def disconnect(self, org) -> bool:
        """Disconnect from Chatwoot."""
        conn = _get_connection(org)
        if conn:
            config = _decrypt_config(conn.config_json or {})
            # Try to remove webhook
            try:
                resp = _api_request(config, "GET", "/webhooks")
                if resp.status_code == 200:
                    from django.conf import settings as django_settings
                    domain = getattr(django_settings, "DOMAIN_NAME", "https://crm.talkhub.me")
                    webhook_prefix = f"{domain}/api/integrations/webhooks/chatwoot/"
                    webhooks = resp.json().get("payload", resp.json() if isinstance(resp.json(), list) else [])
                    for wh in webhooks:
                        wh_url = wh.get("url", "")
                        if wh_url.startswith(webhook_prefix) or wh_url == webhook_prefix:
                            _api_request(config, "DELETE", f"/webhooks/{wh['id']}")
                            logger.info("Chatwoot webhook removed (id=%s) for org %s", wh["id"], org.id)
            except Exception as exc:
                logger.warning("Could not remove Chatwoot webhook: %s", exc)

        return True

    def sync(self, org, sync_type: str, job_id: str) -> dict:
        """Import conversations from Chatwoot into the CRM."""
        conn = _get_connection(org)
        if not conn:
            return {"status": "FAILED", "total": 0, "imported": 0, "updated": 0, "skipped": 0, "errors": 0,
                    "message": "Chatwoot não está conectado."}

        config = _decrypt_config(conn.config_json or {})

        # Ensure ChannelConfig exists (backfill for connections created before this code)
        from channels.models import ChannelConfig
        ChannelConfig.objects.update_or_create(
            org=org,
            channel_type="chatwoot",
            defaults={
                "provider": "chatwoot",
                "display_name": "Chatwoot",
                "is_active": True,
                "config_json": {"account_id": config.get("account_id")},
                "capabilities_json": ["text", "image", "file"],
            },
        )
        total_imported = 0
        total_records = 0

        # Load cursor state for resumable sync
        from integrations.models import SyncJob
        job = None
        cursor = {}
        if job_id:
            try:
                job = SyncJob.objects.get(id=job_id)
                cursor = job.cursor_state or {}
            except SyncJob.DoesNotExist:
                pass

        statuses = ["open", "pending", "resolved", "snoozed"]
        start_status_idx = cursor.get("status_idx", 0)
        start_page = cursor.get("page", 1)
        total_imported = cursor.get("imported", 0)
        total_records = cursor.get("total", 0)

        try:
            # Step 0: Deduplicate existing contacts (only on fresh sync)
            if not cursor:
                deduped = self._dedup_contacts(org)
                if deduped:
                    logger.info("Chatwoot sync: merged %d duplicate contacts for org %s", deduped, org.id)
            else:
                deduped = 0

            # Fetch conversations for ALL statuses (Chatwoot defaults to 'open' only)
            for si, conv_status in enumerate(statuses[start_status_idx:], start_status_idx):
                page = start_page if si == start_status_idx else 1
                max_pages = 50  # Safety limit
                while page <= max_pages:
                    resp = _api_request(config, "GET", "/conversations", params={
                        "page": page, "status": conv_status,
                    })
                    if resp.status_code != 200:
                        logger.error("Chatwoot sync: failed to fetch %s conversations page %d: %s",
                                     conv_status, page, resp.status_code)
                        break

                    data = resp.json().get("data", resp.json())
                    payload = data.get("payload", data) if isinstance(data, dict) else data
                    conversations = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []

                    if not conversations:
                        break

                    total_records += len(conversations)
                    logger.info("Chatwoot sync: page %d status=%s returned %d conversations",
                                page, conv_status, len(conversations))

                    for cw_conv in conversations:
                        try:
                            imported = self._import_conversation(org, config, cw_conv)
                            if imported:
                                total_imported += 1
                        except Exception as exc:
                            logger.error("Chatwoot sync: error importing conversation %s: %s", cw_conv.get("id"), exc)

                    # Save checkpoint after each page for resumable sync
                    if job:
                        job.cursor_state = {
                            "status_idx": si, "page": page + 1,
                            "imported": total_imported, "total": total_records,
                        }
                        job.imported_count = total_imported
                        job.save(update_fields=["cursor_state", "imported_count", "updated_at"])

                    # Check if there are more pages
                    meta = data.get("meta", {}) if isinstance(data, dict) else {}
                    all_count = meta.get("all_count", 0)
                    if not all_count or len(conversations) < 25:
                        break
                    page += 1

            # Also sync contacts from Chatwoot
            contacts_imported = self._sync_contacts(org, config)

            logger.info(
                "Chatwoot sync complete for org %s: %d/%d conversations, %d contacts imported, %d duplicates merged",
                org.id, total_imported, total_records, contacts_imported, deduped,
            )
            dedup_msg = f" {deduped} duplicatas removidas." if deduped else ""
            return {
                "status": "COMPLETED",
                "total": total_records, "imported": total_imported,
                "updated": 0, "skipped": total_records - total_imported, "errors": 0,
                "contacts_imported": contacts_imported, "deduped": deduped,
                "message": f"{total_imported} conversas importadas de {total_records}. {contacts_imported} contatos sincronizados.{dedup_msg}",
            }

        except Exception as exc:
            logger.error("Chatwoot sync failed for org %s: %s", org.id, exc)
            return {"status": "FAILED", "total": total_records, "imported": total_imported,
                    "updated": 0, "skipped": 0, "errors": 1,
                    "message": f"Erro ao sincronizar: {exc}"}

    def _sync_contacts(self, org, config):
        """Import contacts from Chatwoot GET /contacts API (paginated)."""
        imported = 0
        page = 1
        max_pages = 50  # Safety limit

        while page <= max_pages:
            try:
                resp = _api_request(config, "GET", "/contacts", params={"page": page})
                if resp.status_code != 200:
                    logger.warning("Chatwoot contacts sync: page %d returned %s", page, resp.status_code)
                    break

                data = resp.json()
                # Chatwoot returns {payload: [...], meta: {}}
                contacts_list = data.get("payload", data) if isinstance(data, dict) else data
                if isinstance(contacts_list, dict):
                    contacts_list = contacts_list.get("data", [])
                if not contacts_list:
                    break

                for cw_contact in contacts_list:
                    try:
                        if not cw_contact.get("name") and not cw_contact.get("email") and not cw_contact.get("phone_number"):
                            continue
                        contact = self._get_or_create_contact(org, cw_contact, update_existing=True)
                        if contact:
                            imported += 1
                    except Exception as exc:
                        logger.warning("Chatwoot contacts sync: error importing contact %s: %s", cw_contact.get("id"), exc)

                # Check pagination
                meta = data.get("meta", {}) if isinstance(data, dict) else {}
                total_pages = 1
                if meta.get("pages"):
                    total_pages = meta["pages"]
                elif meta.get("all_count") and meta.get("per_page"):
                    total_pages = (meta["all_count"] + meta["per_page"] - 1) // meta["per_page"]

                if page >= total_pages:
                    break
                page += 1

            except Exception as exc:
                logger.error("Chatwoot contacts sync failed at page %d: %s", page, exc)
                break

        logger.info("Chatwoot contacts sync: %d contacts imported for org %s", imported, org.id)
        return imported

    def _import_conversation(self, org, config, cw_conv):
        """Import a single Chatwoot conversation into the CRM."""
        from contacts.models import Contact
        from conversations.models import Conversation, Message

        cw_conv_id = cw_conv.get("id")
        if not cw_conv_id:
            return False

        # Detect group conversations (multiple heuristics)
        additional_attrs = cw_conv.get("additional_attributes", {}) or {}
        cw_contact = cw_conv.get("meta", {}).get("sender") or cw_conv.get("contact", {})
        contact_name = (cw_contact.get("name") or "") if cw_contact else ""

        is_group = (
            cw_conv.get("conversation_type") == "group"
            or additional_attrs.get("type") == "group"
            or bool(additional_attrs.get("chat_name_or_title"))
            or bool(additional_attrs.get("group_name"))
            or "(GROUP)" in contact_name.upper()  # Chatwoot appends (GROUP) to group names
        )

        # Preserve Chatwoot contact ID for dedup
        cw_contact_id = cw_contact.get("id") if cw_contact else None

        if is_group or not cw_contact or not (contact_name or cw_contact.get("email") or cw_contact.get("phone_number")):
            group_name = (
                additional_attrs.get("chat_name_or_title")
                or additional_attrs.get("group_name")
                or cw_conv.get("meta", {}).get("sender", {}).get("name")
                or contact_name
                or f"Grupo #{cw_conv_id}"
            )
            cw_contact = {
                "id": cw_contact_id,
                "name": group_name,
                "phone_number": cw_contact.get("phone_number", "") if cw_contact else "",
                "email": cw_contact.get("email", "") if cw_contact else "",
            }

        contact = self._get_or_create_contact(org, cw_contact)
        if not contact:
            return False

        # Map Chatwoot status to CRM status
        status_map = {"open": "open", "pending": "pending", "resolved": "resolved", "snoozed": "pending"}
        cw_status = cw_conv.get("status", "open")

        # Get or create conversation
        conv, created = Conversation.objects.update_or_create(
            org=org,
            channel="chatwoot",
            metadata_json__chatwoot_conversation_id=cw_conv_id,
            defaults={
                "contact": contact,
                "integration_provider": "chatwoot",
                "status": status_map.get(cw_status, "open"),
                "metadata_json": {
                    "chatwoot_conversation_id": cw_conv_id,
                    "chatwoot_inbox_id": cw_conv.get("inbox_id"),
                    "chatwoot_account_id": config.get("account_id"),
                    "is_group": is_group,
                    "conversation_type": cw_conv.get("conversation_type", ""),
                },
            },
        )

        # Fetch messages for this conversation
        try:
            resp = _api_request(config, "GET", f"/conversations/{cw_conv_id}/messages")
            if resp.status_code == 200:
                messages_data = resp.json().get("payload", resp.json())
                messages_list = messages_data if isinstance(messages_data, list) else messages_data.get("data", []) if isinstance(messages_data, dict) else []

                for cw_msg in messages_list:
                    self._import_message(org, conv, cw_msg)

                # Update last_message_at
                if messages_list:
                    conv.last_message_at = timezone.now()
                    conv.save(update_fields=["last_message_at"])
        except Exception as exc:
            logger.warning("Failed to fetch messages for Chatwoot conversation %s: %s", cw_conv_id, exc)

        return True

    def _dedup_contacts(self, org):
        """Merge duplicate contacts that have no email and no phone (groups).

        Keeps the oldest contact and reassigns conversations from duplicates.
        Returns the number of duplicates removed.
        """
        from contacts.models import Contact
        from conversations.models import Conversation
        from django.db.models import Count, Min, Q

        # Find contacts with no email and no phone that share the same name
        dupes = (
            Contact.objects.filter(org=org)
            .filter(Q(email__isnull=True) | Q(email=""))
            .filter(Q(phone__isnull=True) | Q(phone=""))
            .values("first_name", "last_name")
            .annotate(cnt=Count("id"), oldest=Min("created_at"))
            .filter(cnt__gt=1)
        )

        total_removed = 0
        for group in dupes:
            contacts = list(
                Contact.objects.filter(
                    org=org,
                    first_name=group["first_name"],
                    last_name=group["last_name"],
                ).filter(
                    Q(email__isnull=True) | Q(email=""),
                ).filter(
                    Q(phone__isnull=True) | Q(phone=""),
                ).order_by("created_at")
            )

            if len(contacts) <= 1:
                continue

            # Keep the first (oldest), merge the rest
            keeper = contacts[0]
            for dup in contacts[1:]:
                # Reassign conversations from duplicate to keeper
                Conversation.objects.filter(org=org, contact=dup).update(contact=keeper)
                # Merge chatwoot_id references into keeper description
                if dup.description and "chatwoot_id:" in (dup.description or ""):
                    keeper_desc = keeper.description or ""
                    for line in (dup.description or "").splitlines():
                        if line.startswith("chatwoot_id:") and line not in keeper_desc:
                            keeper_desc = f"{keeper_desc}\n{line}".strip()
                    keeper.description = keeper_desc
                    keeper.save(update_fields=["description", "updated_at"])
                dup.delete()
                total_removed += 1

            logger.info(
                "Dedup: merged %d duplicates of '%s %s' into contact %s",
                len(contacts) - 1, group["first_name"], group["last_name"], keeper.id,
            )

        return total_removed

    def _get_or_create_contact(self, org, cw_contact, update_existing=True):
        """Get or create a CRM contact from Chatwoot contact data. Optionally update missing fields."""
        from contacts.models import Contact, ContactEmail, ContactPhone

        if not cw_contact:
            return None

        email = (cw_contact.get("email") or "").strip()
        phone = (cw_contact.get("phone_number") or "").strip()
        name = (cw_contact.get("name") or "").strip()
        cw_id = cw_contact.get("id")  # Chatwoot contact ID

        # Pre-compute name parts for lookups
        parts = name.split(" ", 1) if name else ["Desconhecido"]
        first_name = parts[0] or "Desconhecido"
        last_name = parts[1] if len(parts) > 1 else ""

        # 1) Try to find by Chatwoot contact ID (most reliable for dedup)
        contact = None
        if cw_id:
            contact = Contact.objects.filter(
                org=org, description__contains=f"chatwoot_id:{cw_id}"
            ).first()

        # 2) Try by email (primary field)
        if not contact and email:
            contact = Contact.objects.filter(org=org, email=email).first()

        # 2b) Try by secondary_email
        if not contact and email:
            contact = Contact.objects.filter(org=org, secondary_email__iexact=email).first()

        # 2c) Try by extra_emails table
        if not contact and email:
            extra = ContactEmail.objects.filter(
                contact__org=org, email__iexact=email
            ).select_related("contact").first()
            if extra:
                contact = extra.contact

        # 3) Try by phone (primary field)
        if not contact and phone:
            contact = Contact.objects.filter(org=org, phone=phone).first()

        # 3b) Try by secondary_phone
        if not contact and phone:
            contact = Contact.objects.filter(org=org, secondary_phone=phone).first()

        # 3c) Try by extra_phones table
        if not contact and phone:
            extra = ContactPhone.objects.filter(
                contact__org=org, phone=phone
            ).select_related("contact").first()
            if extra:
                contact = extra.contact

        # 4) For contacts without email/phone (groups), try by exact name
        #    Check both NULL and empty-string variants for email/phone
        if not contact and name and not email and not phone:
            contact = Contact.objects.filter(
                org=org, first_name=first_name, last_name=last_name,
            ).filter(
                Q(email__isnull=True) | Q(email=""),
            ).filter(
                Q(phone__isnull=True) | Q(phone=""),
            ).first()

        if contact:
            if update_existing:
                # Fill in missing fields from Chatwoot data
                updated_fields = []
                if email and not contact.email:
                    contact.email = email
                    updated_fields.append("email")
                if phone and not contact.phone:
                    contact.phone = phone
                    updated_fields.append("phone")
                if name and contact.first_name == "Desconhecido":
                    contact.first_name = first_name
                    contact.last_name = last_name
                    updated_fields.extend(["first_name", "last_name"])
                # Store chatwoot_id reference if not already present
                if cw_id and (not contact.description or f"chatwoot_id:{cw_id}" not in (contact.description or "")):
                    desc = (contact.description or "").strip()
                    contact.description = f"{desc}\nchatwoot_id:{cw_id}".strip()
                    if "description" not in updated_fields:
                        updated_fields.append("description")
                if updated_fields:
                    updated_fields.append("updated_at")
                    contact.save(update_fields=updated_fields)
                    logger.info("Updated contact %s with Chatwoot data: %s", contact.id, updated_fields)
            return contact

        # Store chatwoot_id in description for future dedup
        description = f"chatwoot_id:{cw_id}" if cw_id else ""

        contact = Contact.objects.create(
            org=org,
            first_name=first_name,
            last_name=last_name,
            email=email or None,
            phone=phone or None,
            description=description,
        )
        logger.info("Created contact %s for Chatwoot contact (org=%s, cw_id=%s)", contact.id, org.id, cw_id)

        return contact

    def _import_message(self, org, conversation, cw_msg):
        """Import a single Chatwoot message into the CRM."""
        from django.db import IntegrityError

        from conversations.models import Message

        cw_msg_id = cw_msg.get("id")
        if not cw_msg_id:
            return

        # Idempotency key for this message
        idem_key = f"chatwoot:{cw_msg_id}"

        # Fast path: check if already imported (avoids IntegrityError in most cases)
        if Message.objects.filter(idempotency_key=idem_key).exists():
            return

        # Legacy dedup fallback (for messages imported before idempotency_key was added)
        if Message.objects.filter(
            org=org,
            conversation=conversation,
            metadata_json__chatwoot_message_id=cw_msg_id,
        ).exists():
            return

        # Map message type
        msg_type_num = cw_msg.get("message_type", 0)
        direction_map = {0: "in", 1: "out", 2: "note", 3: "system"}
        direction = direction_map.get(msg_type_num, "in")

        content = cw_msg.get("content") or ""
        content_type = cw_msg.get("content_type", "text")

        # Handle attachments
        media_url = None
        msg_type = "text"
        attachments = cw_msg.get("attachments", [])
        if attachments:
            first_att = attachments[0]
            media_url = first_att.get("data_url", "")
            file_type = first_att.get("file_type", "")
            if file_type == "image":
                msg_type = "image"
            elif file_type in ("video", "audio"):
                msg_type = file_type
            else:
                msg_type = "file"

        # Get sender info
        sender = cw_msg.get("sender", {}) or {}
        sender_name = sender.get("name", "")
        sender_id = str(sender.get("id", ""))

        created_at = cw_msg.get("created_at")
        timestamp = timezone.now()
        if created_at:
            try:
                if isinstance(created_at, (int, float)):
                    from datetime import datetime
                    timestamp = timezone.make_aware(datetime.fromtimestamp(created_at))
                else:
                    from django.utils.dateparse import parse_datetime
                    parsed = parse_datetime(str(created_at))
                    if parsed:
                        timestamp = parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
            except (ValueError, OSError):
                pass

        try:
            msg = Message.objects.create(
                org=org,
                conversation=conversation,
                direction=direction,
                msg_type=msg_type,
                content=content,
                media_url=media_url,
                sender_type=sender.get("type", ""),
                sender_name=sender_name,
                sender_id=sender_id,
                timestamp=timestamp,
                idempotency_key=idem_key,
                metadata_json={
                    "chatwoot_message_id": cw_msg_id,
                    "chatwoot_content_type": content_type,
                },
            )
            # Broadcast via WebSocket
            try:
                from conversations.broadcast import broadcast_new_message
                from conversations.serializers import MessageSerializer

                broadcast_new_message(
                    str(org.id),
                    str(conversation.id),
                    MessageSerializer(msg).data,
                )
            except Exception:
                pass
        except IntegrityError:
            # UNIQUE constraint violation — message already exists (race condition handled)
            logger.info("Duplicate message skipped (IntegrityError): %s", idem_key)

    def get_status(self, org) -> dict:
        from integrations.models import IntegrationConnection

        conn = IntegrationConnection.objects.filter(
            org=org, connector_slug=self.slug
        ).first()
        if not conn:
            return {"is_connected": False}
        return {
            "is_connected": conn.is_connected,
            "last_sync_at": conn.last_sync_at,
        }

    def get_health(self, org) -> dict:
        conn = _get_connection(org)
        if not conn:
            return {"status": "unknown", "error_count": 0}

        config = _decrypt_config(conn.config_json or {})
        if not config.get("chatwoot_url") or not config.get("api_access_token"):
            return {"status": "down", "error_count": 1}

        try:
            resp = _api_request(config, "GET", "/agents")
            if resp.status_code == 200:
                return {"status": "healthy", "error_count": 0}
            return {"status": "degraded", "error_count": conn.error_count}
        except Exception:
            return {"status": "degraded", "error_count": conn.error_count}

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "fields": [
                {
                    "name": "chatwoot_url",
                    "type": "text",
                    "label": "URL do Chatwoot",
                    "placeholder": "https://chat.talkhub.me",
                    "required": True,
                    "description": "URL completa da instância Chatwoot.",
                },
                {
                    "name": "api_access_token",
                    "type": "password",
                    "label": "Token de Acesso (API)",
                    "placeholder": "",
                    "required": True,
                    "description": "Personal Access Token do Chatwoot (Perfil → Access Token).",
                    "secret": True,
                },
                {
                    "name": "account_id",
                    "type": "number",
                    "label": "ID da Conta",
                    "placeholder": "1",
                    "required": True,
                    "description": "ID numérico da conta Chatwoot.",
                },
                {
                    "name": "pubsub_token",
                    "type": "text",
                    "label": "Token de Tempo Real (PubSub)",
                    "placeholder": "",
                    "required": False,
                    "description": "Permite mensagens instantâneas sem recarregar. Extraído automaticamente do perfil Chatwoot.",
                },
                {
                    "name": "webhook_secret",
                    "type": "password",
                    "label": "Webhook Secret (opcional)",
                    "placeholder": "",
                    "required": False,
                    "description": "Secret para validar webhooks via HMAC-SHA256 (opcional).",
                    "secret": True,
                },
            ],
            "required": ["chatwoot_url", "api_access_token", "account_id"],
        }

    def handle_webhook(self, org, payload: dict, headers: dict) -> Any:
        """Process Chatwoot webhook events."""
        event = payload.get("event", "")
        logger.info("Chatwoot webhook: event=%s for org %s", event, org.id)

        if event == "message_created":
            return self._handle_message_created(org, payload)
        elif event == "message_updated":
            return self._handle_message_updated(org, payload)
        elif event == "conversation_created":
            return self._handle_conversation_created(org, payload)
        elif event == "conversation_updated":
            return self._handle_conversation_updated(org, payload)
        elif event == "conversation_status_changed":
            return self._handle_conversation_status_changed(org, payload)
        elif event in ("contact_created", "contact_updated"):
            return self._handle_contact_event(org, payload)
        else:
            logger.info("Chatwoot webhook: unhandled event %s", event)
            return {"status": "ignored", "event": event}

    def _extract_contact_info(self, data, cw_conv_id=None, org=None):
        """Extract contact info from webhook payload, handling both individual and group conversations."""
        sender = data.get("sender", {}) or {}

        # Enrich incomplete sender data via Chatwoot API when name is missing
        if sender.get("id") and not sender.get("name") and org:
            try:
                conn = _get_connection(org)
                if conn:
                    config = _decrypt_config(conn.config_json or {})
                    resp = _api_request(config, "GET", f"/contacts/{sender['id']}")
                    if resp.status_code == 200:
                        sender = resp.json()
                        logger.info("Enriched contact %s from Chatwoot API", sender.get("id"))
                    else:
                        logger.warning("Failed to enrich contact %s: HTTP %s", sender["id"], resp.status_code)
            except Exception as e:
                logger.warning("Failed to enrich contact %s: %s", sender.get("id"), e)

        cw_conv = data.get("conversation", {}) or data
        additional_attrs = (
            cw_conv.get("additional_attributes", {})
            or data.get("additional_attributes", {})
            or {}
        )

        # Get Chatwoot contact ID for dedup
        contact_id = (
            sender.get("id")
            or cw_conv.get("meta", {}).get("sender", {}).get("id")
            or (data.get("contact", {}).get("id") if isinstance(data.get("contact"), dict) else None)
        )
        sender_name = sender.get("name", "") if sender else ""

        # Check if this is a group conversation (multiple heuristics)
        is_group = (
            cw_conv.get("conversation_type") == "group"
            or data.get("conversation_type") == "group"
            or additional_attrs.get("type") == "group"
            or bool(additional_attrs.get("chat_name_or_title"))
            or bool(additional_attrs.get("group_name"))
            or "(GROUP)" in sender_name.upper()
        )

        if is_group or not sender or not (sender.get("name") or sender.get("email") or sender.get("phone_number")):
            # Try multiple sources for group name
            group_name = (
                additional_attrs.get("chat_name_or_title")
                or additional_attrs.get("group_name")
                or cw_conv.get("meta", {}).get("sender", {}).get("name")
                or cw_conv.get("meta", {}).get("channel")
                or (sender.get("name") if sender else None)
                or f"Grupo #{cw_conv_id or cw_conv.get('id', '?')}"
            )
            return {
                "id": contact_id,
                "name": group_name,
                "phone_number": sender.get("phone_number", ""),
                "email": sender.get("email", ""),
            }, True

        # Ensure sender dict has the ID for dedup
        if contact_id and "id" not in sender:
            sender = dict(sender)
            sender["id"] = contact_id
        return sender, False

    def _handle_message_created(self, org, payload):
        """Handle message_created webhook event."""
        from conversations.models import Conversation, Message

        data = payload
        msg_type_num = data.get("message_type")

        # Skip outgoing messages sent by us (echo prevention — fast path)
        if msg_type_num == 1:
            content_attrs = data.get("content_attributes", {}) or {}
            additional_attrs = data.get("additional_attributes", {}) or {}
            if content_attrs.get("external_created") or additional_attrs.get("external_created"):
                return {"status": "skipped", "reason": "echo"}

        # Robust idempotency check via crm_idempotency_key
        additional_attrs = data.get("additional_attributes", {}) or {}
        crm_key = additional_attrs.get("crm_idempotency_key")
        if crm_key and Message.objects.filter(idempotency_key=crm_key).exists():
            return {"status": "skipped", "reason": "idempotent_crm_key"}

        cw_conv = data.get("conversation", {})
        cw_conv_id = cw_conv.get("id") or data.get("conversation_id")
        if not cw_conv_id:
            return {"status": "error", "message": "No conversation_id in payload"}

        account_id = payload.get("account", {}).get("id")

        # Find or create conversation
        conv = Conversation.objects.filter(
            org=org, channel="chatwoot",
            metadata_json__chatwoot_conversation_id=cw_conv_id,
        ).first()

        if not conv:
            # Extract contact info (handles individuals and groups)
            contact_info, is_group = self._extract_contact_info(data, cw_conv_id, org=org)
            logger.info(
                "Chatwoot new conversation %s: is_group=%s, conv_type=%s, additional_attrs=%s",
                cw_conv_id, is_group,
                cw_conv.get("conversation_type"),
                {k: v for k, v in (cw_conv.get("additional_attributes") or {}).items()
                 if k in ("type", "chat_name_or_title", "group_name")},
            )

            contact = self._get_or_create_contact(org, contact_info)
            if not contact:
                return {"status": "error", "message": "Could not identify contact"}

            conv = Conversation.objects.create(
                org=org,
                contact=contact,
                channel="chatwoot",
                integration_provider="chatwoot",
                status="open",
                metadata_json={
                    "chatwoot_conversation_id": cw_conv_id,
                    "chatwoot_inbox_id": cw_conv.get("inbox_id"),
                    "chatwoot_account_id": account_id,
                    "is_group": is_group,
                    "conversation_type": cw_conv.get("conversation_type", ""),
                },
            )

        # Import the message
        self._import_message(org, conv, data)

        # Update conversation timestamp
        conv.last_message_at = timezone.now()
        conv.save(update_fields=["last_message_at"])

        # Notify frontend via cache flag
        self._notify_new_message(org, conv)

        return {"status": "processed", "event": "message_created", "conversation_id": str(conv.id)}

    def _handle_message_updated(self, org, payload):
        """Handle message_updated webhook event — update content of existing message."""
        from conversations.models import Message

        data = payload
        cw_msg_id = data.get("id")
        if not cw_msg_id:
            return {"status": "error", "message": "No message id"}

        cw_conv = data.get("conversation", {})
        cw_conv_id = cw_conv.get("id") or data.get("conversation_id")

        msg = Message.objects.filter(
            org=org,
            metadata_json__chatwoot_message_id=cw_msg_id,
        ).first()

        if not msg:
            # Message not found — might be a new message, treat as created
            if cw_conv_id:
                return self._handle_message_created(org, payload)
            return {"status": "skipped", "reason": "message_not_found"}

        # Update content and attachments
        new_content = data.get("content")
        updated_fields = []

        if new_content is not None and new_content != msg.content:
            msg.content = new_content
            updated_fields.append("content")

        # Update attachments if changed
        attachments = data.get("attachments", [])
        if attachments:
            first_att = attachments[0]
            new_media_url = first_att.get("data_url", "")
            if new_media_url and new_media_url != msg.media_url:
                msg.media_url = new_media_url
                updated_fields.append("media_url")

        if updated_fields:
            updated_fields.append("updated_at")
            msg.save(update_fields=updated_fields)

        return {"status": "processed", "event": "message_updated"}

    def _handle_conversation_created(self, org, payload):
        """Handle conversation_created webhook event."""
        from conversations.models import Conversation

        data = payload
        cw_conv_id = data.get("id") or data.get("conversation", {}).get("id")
        if not cw_conv_id:
            return {"status": "error", "message": "No conversation id"}

        account_id = payload.get("account", {}).get("id")

        # Check if already exists
        existing = Conversation.objects.filter(
            org=org, channel="chatwoot",
            metadata_json__chatwoot_conversation_id=cw_conv_id,
        ).exists()
        if existing:
            return {"status": "skipped", "reason": "already_exists"}

        # Extract contact info (handles individuals and groups)
        contact_info, is_group = self._extract_contact_info(data, cw_conv_id, org=org)

        # Also try meta.sender and contact fields for individual conversations
        if not is_group:
            cw_contact = data.get("meta", {}).get("sender") or data.get("contact", {})
            if cw_contact and (cw_contact.get("name") or cw_contact.get("email") or cw_contact.get("phone_number")):
                contact_info = cw_contact

        contact = self._get_or_create_contact(org, contact_info)
        if not contact:
            return {"status": "error", "message": "Could not identify contact"}

        status_map = {"open": "open", "pending": "pending", "resolved": "resolved", "snoozed": "pending"}

        conv = Conversation.objects.create(
            org=org,
            contact=contact,
            channel="chatwoot",
            integration_provider="chatwoot",
            status=status_map.get(data.get("status", "open"), "open"),
            metadata_json={
                "chatwoot_conversation_id": cw_conv_id,
                "chatwoot_inbox_id": data.get("inbox_id"),
                "chatwoot_account_id": account_id,
                "is_group": is_group,
                "conversation_type": data.get("conversation_type", ""),
            },
        )

        self._notify_new_message(org, conv)
        return {"status": "processed", "event": "conversation_created"}

    def _should_skip_status_sync(self, conv):
        """Check if a recent local status change should take precedence over Chatwoot."""
        meta = conv.metadata_json or {}
        local_changed = meta.get("status_changed_locally_at")
        if not local_changed:
            return False
        try:
            from django.utils.dateparse import parse_datetime
            changed_at = parse_datetime(local_changed)
            if changed_at and (timezone.now() - changed_at).total_seconds() < 30:
                return True
        except (ValueError, TypeError):
            pass
        return False

    def _handle_conversation_updated(self, org, payload):
        """Handle conversation_updated webhook event — sync assignee, labels, etc."""
        from conversations.models import Conversation

        data = payload
        cw_conv_id = data.get("id") or data.get("conversation", {}).get("id")
        if not cw_conv_id:
            return {"status": "error", "message": "No conversation id"}

        conv = Conversation.objects.filter(
            org=org, channel="chatwoot",
            metadata_json__chatwoot_conversation_id=cw_conv_id,
        ).first()

        if not conv:
            # Conversation doesn't exist yet — create it
            return self._handle_conversation_created(org, payload)

        updated_fields = []

        # Sync status — but respect local overrides (30s grace period)
        status_map = {"open": "open", "pending": "pending", "resolved": "resolved", "snoozed": "pending"}
        new_status = data.get("status", "")
        if new_status in status_map and conv.status != status_map[new_status]:
            if not self._should_skip_status_sync(conv):
                conv.status = status_map[new_status]
                updated_fields.append("status")

        # Sync assignee from Chatwoot
        cw_assignee = data.get("meta", {}).get("assignee") or data.get("assignee")
        if cw_assignee:
            # Store Chatwoot assignee info in metadata for reference
            meta = conv.metadata_json or {}
            meta["chatwoot_assignee"] = {
                "id": cw_assignee.get("id"),
                "name": cw_assignee.get("name", ""),
                "email": cw_assignee.get("email", ""),
            }
            conv.metadata_json = meta
            updated_fields.append("metadata_json")

        # Sync labels from Chatwoot
        cw_labels = data.get("labels", [])
        if cw_labels:
            meta = conv.metadata_json or {}
            meta["chatwoot_labels"] = cw_labels
            conv.metadata_json = meta
            if "metadata_json" not in updated_fields:
                updated_fields.append("metadata_json")

        if updated_fields:
            updated_fields.append("updated_at")
            conv.save(update_fields=updated_fields)

        self._notify_new_message(org, conv)
        return {"status": "processed", "event": "conversation_updated"}

    def _handle_conversation_status_changed(self, org, payload):
        """Handle conversation_status_changed webhook event."""
        from conversations.models import Conversation

        data = payload
        cw_conv_id = data.get("id") or data.get("conversation", {}).get("id")
        if not cw_conv_id:
            return {"status": "error", "message": "No conversation id"}

        conv = Conversation.objects.filter(
            org=org, channel="chatwoot",
            metadata_json__chatwoot_conversation_id=cw_conv_id,
        ).first()

        if not conv:
            return {"status": "skipped", "reason": "conversation_not_found"}

        # Respect local status overrides (30s grace period)
        if self._should_skip_status_sync(conv):
            self._notify_new_message(org, conv)
            return {"status": "skipped", "reason": "local_status_override"}

        status_map = {"open": "open", "pending": "pending", "resolved": "resolved", "snoozed": "pending"}
        new_status = data.get("status", "")
        if new_status in status_map:
            conv.status = status_map[new_status]
            conv.save(update_fields=["status", "updated_at"])

        self._notify_new_message(org, conv)
        return {"status": "processed", "event": "conversation_status_changed"}

    def _handle_contact_event(self, org, payload):
        """Handle contact_created/contact_updated webhook events."""
        data = payload
        cw_contact = data if data.get("name") or data.get("email") else data.get("contact", data)
        self._get_or_create_contact(org, cw_contact)
        return {"status": "processed", "event": payload.get("event")}

    def _notify_new_message(self, org, conversation):
        """Set a cache flag to notify the frontend of new messages."""
        try:
            from django.core.cache import cache
            # Set a per-org notification flag that expires after 60 seconds
            cache_key = f"conv_updates:{org.id}"
            cache.set(cache_key, {
                "conversation_id": str(conversation.id),
                "timestamp": timezone.now().isoformat(),
            }, timeout=60)
        except Exception:
            pass  # Non-critical — frontend will still poll

    def validate_webhook(self, payload: bytes, headers: dict, secret: str) -> bool:
        """Validate Chatwoot webhook via HMAC-SHA256 if secret is configured.

        Chatwoot signature format (2025+):
          X-Chatwoot-Signature: sha256=HMAC-SHA256(secret, "{timestamp}.{raw_body}")
          X-Chatwoot-Timestamp: unix-timestamp (seconds)
        """
        if not secret:
            logger.warning("Chatwoot webhook: no secret configured — accepting without signature verification")
            return True

        signature = headers.get("X-Chatwoot-Signature", "") or headers.get("x-chatwoot-signature", "")
        if not signature:
            logger.warning("Chatwoot webhook: no signature header, but secret is configured")
            return False

        raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        timestamp = headers.get("X-Chatwoot-Timestamp", "") or headers.get("x-chatwoot-timestamp", "")

        # New format: sha256=HMAC(secret, "{timestamp}.{body}")
        if signature.startswith("sha256=") and timestamp:
            sig_hex = signature[len("sha256="):]
            message = f"{timestamp}.".encode("utf-8") + raw
            expected = hmac.HMAC(
                secret.encode("utf-8"), message, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, sig_hex)

        # Legacy fallback: HMAC(secret, body) — no prefix, no timestamp
        expected = hmac.HMAC(
            secret.encode("utf-8"), raw, hashlib.sha256
        ).hexdigest()
        sig_clean = signature[len("sha256="):] if signature.startswith("sha256=") else signature
        return hmac.compare_digest(expected, sig_clean)

    def get_sync_types(self) -> list[str]:
        return ["full"]
