"""
Data Unifier — Motor de concatenação e enriquecimento de dados.

Responsável por:
1. Normalizar dados de QUALQUER fonte usando o variable_registry
2. Concatenar/enriquecer Contact e Account com dados de integrações
3. Auto-linkar Contact ↔ Account baseado em organization/company_name
4. Deduplicar e mesclar dados de múltiplas fontes
5. Respeitar estratégia de conflito configurada por org

Fluxo:
    dados_externos → normalize_incoming() → enrich_contact() / enrich_account()
                                          → auto_link_contact_account()

Uso:
    from integrations.data_unifier import DataUnifier
    unifier = DataUnifier(org)
    contact = unifier.upsert_contact(external_data, source="talkhub_omni")
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from integrations.conflict_resolver import (
    detect_conflict,
    log_conflict,
    resolve_conflict,
    set_sync_lock,
)
from integrations.field_transforms import (
    apply_field_mapping,
    format_phone,
    split_full_name,
)
from integrations.variable_registry import (
    ACCOUNT_SCHEMA,
    CONTACT_SCHEMA,
    LEAD_TO_ACCOUNT_MAP,
    LEAD_TO_CONTACT_MAP,
    VariableSource,
    resolve_variable,
)

logger = logging.getLogger(__name__)


class DataUnifier:
    """
    Motor central de unificação de dados do sistema integrativo.

    Garante que dados de qualquer fonte (TalkHub, webhook, CSV, Lead conversion)
    sejam normalizados e concatenados nos modelos Contact e Account de forma
    consistente.
    """

    def __init__(self, org, connector_slug: str = "system", conflict_strategy: str | None = None):
        """
        Args:
            org: Instância de Org.
            connector_slug: Slug do conector de origem.
            conflict_strategy: Estratégia de conflito (None = buscar da IntegrationConnection).
        """
        self.org = org
        self.connector_slug = connector_slug
        self._conflict_strategy = conflict_strategy

    @property
    def conflict_strategy(self) -> str:
        """Obter estratégia de conflito (lazy load da IntegrationConnection)."""
        if self._conflict_strategy:
            return self._conflict_strategy

        from integrations.models import IntegrationConnection

        conn = IntegrationConnection.objects.filter(
            org=self.org, connector_slug=self.connector_slug
        ).first()
        self._conflict_strategy = conn.conflict_strategy if conn else "last_write_wins"
        return self._conflict_strategy

    # ─── NORMALIZAÇÃO ────────────────────────────────────────────────────

    def normalize_incoming(
        self, raw_data: dict, entity_type: str = "contact"
    ) -> dict[str, Any]:
        """
        Normalizar dados de entrada usando o variable_registry.

        Resolve aliases, aplica transformações, e retorna dict com
        campos CRM canônicos.

        Args:
            raw_data: Dados brutos da fonte externa.
            entity_type: "contact" ou "account".

        Returns:
            Dict com campos CRM normalizados.
        """
        normalized: dict[str, Any] = {}

        for key, value in raw_data.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            mapping = resolve_variable(entity_type, key)
            if not mapping:
                continue

            # Aplicar transformação se configurada
            if mapping.transform == "split":
                parts = split_full_name(str(value))
                normalized.setdefault("first_name", parts["first_name"])
                normalized.setdefault("last_name", parts["last_name"])
            elif mapping.transform == "phone_format":
                country = raw_data.get("country", "BR")
                normalized[mapping.crm_field] = format_phone(str(value), country)
            elif mapping.transform == "number":
                try:
                    normalized[mapping.crm_field] = float(value)
                except (ValueError, TypeError):
                    pass
            else:
                normalized[mapping.crm_field] = str(value).strip()

        return normalized

    # ─── CONTACT UPSERT ──────────────────────────────────────────────────

    @transaction.atomic
    def upsert_contact(
        self,
        external_data: dict,
        source: str = "",
        talkhub_subscriber_id: str | None = None,
    ) -> tuple[Any, bool]:
        """
        Criar ou atualizar Contact com dados normalizados.

        Estratégia de lookup (em ordem):
        1. talkhub_subscriber_id (se fornecido)
        2. email (unique per org)
        3. phone (fallback)
        4. Criar novo

        Args:
            external_data: Dados brutos ou já normalizados.
            source: Fonte dos dados (para tracking).
            talkhub_subscriber_id: ID do subscriber TalkHub (se aplicável).

        Returns:
            Tuple (contact, created).
        """
        from contacts.models import Contact

        normalized = self.normalize_incoming(external_data, "contact")

        if not normalized.get("first_name"):
            logger.warning("Contact upsert skipped: first_name is required. Data: %s", external_data)
            return None, False

        # Lookup existente
        contact = self._find_existing_contact(normalized, talkhub_subscriber_id)
        created = False

        if contact:
            # Enriquecer contact existente
            contact = self._enrich_contact(contact, normalized, source)
        else:
            # Criar novo contact
            contact = Contact(
                org=self.org,
                first_name=normalized.get("first_name", ""),
                last_name=normalized.get("last_name", ""),
            )
            self._apply_fields(contact, normalized, skip={"first_name", "last_name"})

            if source:
                contact.source = source
            if talkhub_subscriber_id:
                contact.talkhub_subscriber_id = talkhub_subscriber_id

            contact.save()
            created = True
            logger.info(
                "Contact created: %s %s (org=%s, source=%s)",
                contact.first_name, contact.last_name, self.org.id, source,
            )

        # Auto-link com Account
        if normalized.get("organization"):
            self._auto_link_contact_account(contact, normalized["organization"])

        # Set sync lock para anti-loop (use subscriber_id for webhook anti-loop)
        lock_key = f"contact:{talkhub_subscriber_id}" if talkhub_subscriber_id else str(contact.id)
        set_sync_lock(lock_key, str(self.org.id))

        return contact, created

    def _find_existing_contact(
        self, normalized: dict, talkhub_subscriber_id: str | None
    ):
        """Buscar contact existente por subscriber_id, email ou phone (including extras)."""
        from contacts.models import Contact, ContactEmail, ContactPhone

        qs = Contact.objects.filter(org=self.org)

        # 1. TalkHub subscriber ID
        if talkhub_subscriber_id:
            contact = qs.filter(talkhub_subscriber_id=talkhub_subscriber_id).first()
            if contact:
                return contact

        # 2. Email (case-insensitive) — primary field
        email = normalized.get("email")
        if email:
            contact = qs.filter(email__iexact=email).first()
            if contact:
                return contact
            # 2b. Check extra_emails table
            extra = ContactEmail.objects.filter(
                contact__org=self.org, email__iexact=email
            ).select_related("contact").first()
            if extra:
                return extra.contact

        # 3. Phone — primary field
        phone = normalized.get("phone")
        if phone:
            contact = qs.filter(phone=phone).first()
            if contact:
                return contact
            # 3b. Check extra_phones table
            extra = ContactPhone.objects.filter(
                contact__org=self.org, phone=phone
            ).select_related("contact").first()
            if extra:
                return extra.contact

        return None

    def _enrich_contact(self, contact, normalized: dict, source: str):
        """
        Enriquecer contact existente com dados novos.

        Regra: preencher campos vazios sem sobrescrever dados existentes,
        exceto quando a estratégia de conflito permite.
        """
        updated_fields = []
        conflicts = {}

        for field_name, new_value in normalized.items():
            if field_name in ("first_name", "last_name") and not new_value:
                continue

            current_value = getattr(contact, field_name, None)

            if not current_value or current_value in ("", None):
                # Campo vazio → preencher
                setattr(contact, field_name, new_value)
                updated_fields.append(field_name)
            elif str(current_value) != str(new_value):
                # Conflito → resolver
                winner, resolved_by = resolve_conflict(
                    crm_value=current_value,
                    external_value=new_value,
                    strategy=self.conflict_strategy,
                    crm_updated_at=contact.updated_at,
                    external_updated_at=timezone.now(),
                )
                if str(winner) != str(current_value):
                    conflicts[field_name] = {
                        "old": current_value,
                        "new": new_value,
                        "resolved_by": resolved_by,
                    }
                    setattr(contact, field_name, winner)
                    updated_fields.append(field_name)

        if updated_fields:
            contact.save(update_fields=updated_fields + ["updated_at"])
            logger.info(
                "Contact enriched: %s (fields=%s, source=%s)",
                contact.id, updated_fields, source,
            )

        if conflicts:
            log_conflict(
                org=self.org,
                connector_slug=self.connector_slug,
                entity_type="contact",
                entity_id=str(contact.id),
                crm_value={k: v["old"] for k, v in conflicts.items()},
                external_value={k: v["new"] for k, v in conflicts.items()},
                resolved_by=list(conflicts.values())[0]["resolved_by"],
                fields_overwritten=list(conflicts.keys()),
            )

        return contact

    # ─── ACCOUNT UPSERT ──────────────────────────────────────────────────

    @transaction.atomic
    def upsert_account(self, external_data: dict) -> tuple[Any, bool]:
        """
        Criar ou atualizar Account com dados normalizados.

        Lookup por name (case-insensitive, unique per org).

        Args:
            external_data: Dados brutos ou já normalizados.

        Returns:
            Tuple (account, created).
        """
        from accounts.models import Account

        normalized = self.normalize_incoming(external_data, "account")

        if not normalized.get("name"):
            logger.warning("Account upsert skipped: name is required. Data: %s", external_data)
            return None, False

        # Lookup por nome (case-insensitive)
        account = Account.objects.filter(
            org=self.org
        ).annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=normalized["name"].lower()
        ).first()

        created = False

        if account:
            account = self._enrich_account(account, normalized)
        else:
            account = Account(org=self.org, name=normalized["name"])
            self._apply_fields(account, normalized, skip={"name"})
            account.save()
            created = True
            logger.info("Account created: %s (org=%s)", account.name, self.org.id)

        set_sync_lock(str(account.id), str(self.org.id))
        return account, created

    def _enrich_account(self, account, normalized: dict):
        """Enriquecer account existente (mesma lógica de conflito do contact)."""
        updated_fields = []

        for field_name, new_value in normalized.items():
            if field_name == "name":
                continue

            current_value = getattr(account, field_name, None)

            if not current_value or current_value in ("", None):
                setattr(account, field_name, new_value)
                updated_fields.append(field_name)
            elif str(current_value) != str(new_value):
                winner, _ = resolve_conflict(
                    crm_value=current_value,
                    external_value=new_value,
                    strategy=self.conflict_strategy,
                    crm_updated_at=account.updated_at,
                    external_updated_at=timezone.now(),
                )
                if str(winner) != str(current_value):
                    setattr(account, field_name, winner)
                    updated_fields.append(field_name)

        if updated_fields:
            account.save(update_fields=updated_fields + ["updated_at"])
            logger.info("Account enriched: %s (fields=%s)", account.id, updated_fields)

        return account

    # ─── AUTO-LINK CONTACT ↔ ACCOUNT ─────────────────────────────────────

    def _auto_link_contact_account(self, contact, company_name: str):
        """
        Auto-linkar Contact com Account baseado no nome da empresa.

        Se o Contact já tem account FK, não sobrescreve.
        Se existe Account com mesmo nome, linka.
        Se não existe, cria Account automaticamente.
        """
        from accounts.models import Account

        if contact.account_id:
            return  # Já linkado

        # Buscar Account existente
        account = Account.objects.filter(
            org=self.org
        ).annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=company_name.strip().lower()
        ).first()

        if not account:
            # Criar Account automaticamente
            account = Account.objects.create(
                org=self.org,
                name=company_name.strip(),
            )
            logger.info(
                "Account auto-created for contact link: %s (org=%s)",
                account.name, self.org.id,
            )

        # Linkar Contact → Account (FK)
        contact.account = account
        contact.save(update_fields=["account", "updated_at"])

        # Adicionar ao M2M contacts do Account
        if not account.contacts.filter(id=contact.id).exists():
            account.contacts.add(contact)

        logger.info(
            "Contact %s auto-linked to Account %s",
            contact.id, account.id,
        )

    # ─── LEAD CONVERSION ─────────────────────────────────────────────────

    @transaction.atomic
    def convert_lead(self, lead) -> dict:
        """
        Converter Lead em Contact + Account usando mapeamento canônico.

        Args:
            lead: Instância de Lead.

        Returns:
            Dict com {contact, account, created_contact, created_account}.
        """
        # Extrair dados do Lead para Contact
        contact_data = {}
        for lead_field, contact_field in LEAD_TO_CONTACT_MAP.items():
            value = getattr(lead, lead_field, None)
            if value:
                contact_data[contact_field] = value

        contact, created_contact = self.upsert_contact(
            contact_data, source="lead_conversion"
        )

        # Extrair dados do Lead para Account
        account = None
        created_account = False
        if lead.company_name:
            account_data = {}
            for lead_field, account_field in LEAD_TO_ACCOUNT_MAP.items():
                value = getattr(lead, lead_field, None)
                if value:
                    account_data[account_field] = value

            account, created_account = self.upsert_account(account_data)

            # Linkar Contact ↔ Account
            if contact and account and not contact.account_id:
                contact.account = account
                contact.save(update_fields=["account", "updated_at"])
                if not account.contacts.filter(id=contact.id).exists():
                    account.contacts.add(contact)

        # Linkar Lead ↔ Contact
        if contact and not lead.contacts.filter(id=contact.id).exists():
            lead.contacts.add(contact)

        logger.info(
            "Lead %s converted: contact=%s (new=%s), account=%s (new=%s)",
            lead.id, contact.id if contact else None, created_contact,
            account.id if account else None, created_account,
        )

        return {
            "contact": contact,
            "account": account,
            "created_contact": created_contact,
            "created_account": created_account,
        }

    # ─── BULK OPERATIONS ─────────────────────────────────────────────────

    def bulk_upsert_contacts(
        self, records: list[dict], source: str = ""
    ) -> dict:
        """
        Upsert em lote de contacts.

        Args:
            records: Lista de dicts com dados externos.
            source: Fonte dos dados.

        Returns:
            Dict com contadores {imported, updated, skipped, errors}.
        """
        counters = {"imported": 0, "updated": 0, "skipped": 0, "errors": 0}

        for record in records:
            try:
                subscriber_id = record.get("talkhub_subscriber_id") or record.get("user_ns")
                contact, created = self.upsert_contact(record, source, subscriber_id)

                if contact is None:
                    counters["skipped"] += 1
                elif created:
                    counters["imported"] += 1
                else:
                    counters["updated"] += 1
            except Exception as e:
                counters["errors"] += 1
                logger.error("Bulk upsert error: %s - %s", record, e)

        return counters

    # ─── HELPERS ──────────────────────────────────────────────────────────

    @staticmethod
    def _apply_fields(instance, data: dict, skip: set | None = None):
        """Aplicar campos normalizados a uma instância de modelo."""
        skip = skip or set()
        for field_name, value in data.items():
            if field_name in skip:
                continue
            if hasattr(instance, field_name):
                setattr(instance, field_name, value)
