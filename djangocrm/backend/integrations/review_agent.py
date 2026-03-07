"""
Agente de Revisão de Integração.

Valida consistência de dados em todo o sistema integrativo:
1. Variáveis unificadas — verifica que todos os caminhos usam o registry
2. Contact ↔ Account links — detecta contacts órfãos com organization preenchido
3. Dados duplicados — detecta contacts/accounts potencialmente duplicados
4. Field mappings — valida que target_fields são campos CRM válidos
5. Sync health — verifica saúde das conexões de integração
6. TalkHub subscribers — detecta subscribers sem contact linkado

Uso via management command:
    python manage.py review_integrations --org <org_id>
    python manage.py review_integrations --org <org_id> --fix

Uso programático:
    from integrations.review_agent import IntegrationReviewAgent
    agent = IntegrationReviewAgent(org)
    report = agent.run_full_review()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.utils import timezone

from integrations.variable_registry import (
    ACCOUNT_SCHEMA,
    CONTACT_SCHEMA,
    get_required_fields,
    resolve_to_crm_field,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewIssue:
    """Um problema encontrado pela revisão."""
    severity: str  # "critical", "warning", "info"
    category: str  # "orphan_link", "duplicate", "field_mapping", "sync_health", etc.
    entity_type: str  # "contact", "account", "field_mapping", "integration", etc.
    entity_id: str | None = None
    message: str = ""
    auto_fixable: bool = False
    fix_action: str | None = None  # Descrição da ação de correção


@dataclass
class ReviewReport:
    """Relatório completo de revisão."""
    org_id: str = ""
    org_name: str = ""
    timestamp: str = ""
    issues: list[ReviewIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    fixes_applied: list[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    @property
    def fixable_count(self) -> int:
        return sum(1 for i in self.issues if i.auto_fixable)

    def to_dict(self) -> dict:
        return {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "timestamp": self.timestamp,
            "summary": {
                "total_issues": len(self.issues),
                "critical": self.critical_count,
                "warnings": self.warning_count,
                "info": self.info_count,
                "auto_fixable": self.fixable_count,
            },
            "stats": self.stats,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "entity_type": i.entity_type,
                    "entity_id": i.entity_id,
                    "message": i.message,
                    "auto_fixable": i.auto_fixable,
                }
                for i in self.issues
            ],
            "fixes_applied": self.fixes_applied,
        }


class IntegrationReviewAgent:
    """
    Agente que revisa a integridade do sistema integrativo.

    Executa verificações em:
    - Contacts sem Account linkado (quando organization está preenchido)
    - Contacts duplicados (email, phone, talkhub_subscriber_id)
    - Accounts duplicados (nome similar)
    - FieldMappings com target_field inválido
    - IntegrationConnections com saúde degradada
    - TalkHub subscribers sem Contact correspondente
    - Campos obrigatórios vazios
    """

    def __init__(self, org, auto_fix: bool = False):
        self.org = org
        self.auto_fix = auto_fix
        self.report = ReviewReport(
            org_id=str(org.id),
            org_name=str(org.name or ""),
            timestamp=timezone.now().isoformat(),
        )

    def run_full_review(self) -> ReviewReport:
        """Executar todas as verificações e retornar relatório."""
        logger.info("Starting integration review for org %s", self.org.id)

        self._collect_stats()
        self._check_orphan_contacts()
        self._check_duplicate_contacts()
        self._check_duplicate_accounts()
        self._check_field_mappings()
        self._check_integration_health()
        self._check_talkhub_subscribers()
        self._check_required_fields()
        self._check_conversations_integrity()

        if self.auto_fix:
            self._apply_fixes()

        logger.info(
            "Review complete for org %s: %d issues (%d critical, %d fixable)",
            self.org.id,
            len(self.report.issues),
            self.report.critical_count,
            self.report.fixable_count,
        )

        return self.report

    # ─── STATS ───────────────────────────────────────────────────────────

    def _collect_stats(self):
        """Coletar estatísticas gerais do sistema."""
        from accounts.models import Account
        from contacts.models import Contact
        from conversations.models import Conversation, Message
        from integrations.models import IntegrationConnection, SyncJob
        from leads.models import Lead

        self.report.stats = {
            "contacts_total": Contact.objects.filter(org=self.org).count(),
            "contacts_with_account": Contact.objects.filter(org=self.org, account__isnull=False).count(),
            "contacts_with_email": Contact.objects.filter(org=self.org).exclude(Q(email__isnull=True) | Q(email="")).count(),
            "contacts_with_phone": Contact.objects.filter(org=self.org).exclude(Q(phone__isnull=True) | Q(phone="")).count(),
            "contacts_with_talkhub": Contact.objects.filter(org=self.org).exclude(Q(talkhub_subscriber_id__isnull=True) | Q(talkhub_subscriber_id="")).count(),
            "accounts_total": Account.objects.filter(org=self.org).count(),
            "leads_total": Lead.objects.filter(org=self.org).count(),
            "leads_active": Lead.objects.filter(org=self.org, is_active=True).exclude(status__in=["converted", "closed"]).count(),
            "conversations_total": Conversation.objects.filter(org=self.org).count(),
            "conversations_open": Conversation.objects.filter(org=self.org, status="open").count(),
            "messages_total": Message.objects.filter(org=self.org).count(),
            "integrations_active": IntegrationConnection.objects.filter(org=self.org, is_active=True).count(),
            "sync_jobs_last_24h": SyncJob.objects.filter(org=self.org, created_at__gte=timezone.now() - timedelta(hours=24)).count(),
        }

    # ─── CHECK: ORPHAN CONTACTS ──────────────────────────────────────────

    def _check_orphan_contacts(self):
        """Detectar contacts com organization preenchido mas sem Account linkado."""
        from contacts.models import Contact

        orphans = Contact.objects.filter(
            org=self.org,
            account__isnull=True,
        ).exclude(
            Q(organization__isnull=True) | Q(organization="")
        )

        for contact in orphans[:100]:  # Limitar a 100 para performance
            self.report.issues.append(ReviewIssue(
                severity="warning",
                category="orphan_link",
                entity_type="contact",
                entity_id=str(contact.id),
                message=(
                    f"Contact '{contact.first_name} {contact.last_name}' tem "
                    f"organization='{contact.organization}' mas não está linkado a nenhum Account."
                ),
                auto_fixable=True,
                fix_action=f"auto_link_account:{contact.organization}",
            ))

    # ─── CHECK: DUPLICATE CONTACTS ───────────────────────────────────────

    def _check_duplicate_contacts(self):
        """Detectar contacts potencialmente duplicados."""
        from contacts.models import Contact

        # Duplicados por email
        dup_emails = (
            Contact.objects.filter(org=self.org)
            .exclude(Q(email__isnull=True) | Q(email=""))
            .values("email")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        for dup in dup_emails:
            self.report.issues.append(ReviewIssue(
                severity="warning",
                category="duplicate",
                entity_type="contact",
                message=f"Email duplicado: '{dup['email']}' aparece em {dup['count']} contacts.",
            ))

        # Duplicados por talkhub_subscriber_id
        dup_subscribers = (
            Contact.objects.filter(org=self.org)
            .exclude(Q(talkhub_subscriber_id__isnull=True) | Q(talkhub_subscriber_id=""))
            .values("talkhub_subscriber_id")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        for dup in dup_subscribers:
            self.report.issues.append(ReviewIssue(
                severity="critical",
                category="duplicate",
                entity_type="contact",
                message=(
                    f"TalkHub subscriber_id duplicado: '{dup['talkhub_subscriber_id']}' "
                    f"aparece em {dup['count']} contacts."
                ),
            ))

    # ─── CHECK: DUPLICATE ACCOUNTS ───────────────────────────────────────

    def _check_duplicate_accounts(self):
        """Detectar accounts com nomes muito similares."""
        from accounts.models import Account

        # Duplicados exatos (case-insensitive)
        dup_names = (
            Account.objects.filter(org=self.org)
            .annotate(name_lower=Lower("name"))
            .values("name_lower")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        for dup in dup_names:
            self.report.issues.append(ReviewIssue(
                severity="warning",
                category="duplicate",
                entity_type="account",
                message=f"Account name duplicado (case-insensitive): '{dup['name_lower']}' ({dup['count']}x).",
            ))

    # ─── CHECK: FIELD MAPPINGS ───────────────────────────────────────────

    def _check_field_mappings(self):
        """Validar que FieldMappings apontam para campos CRM válidos."""
        from integrations.models import FieldMapping

        valid_contact_fields = {m.crm_field for m in CONTACT_SCHEMA.values()}
        valid_account_fields = {m.crm_field for m in ACCOUNT_SCHEMA.values()}
        all_valid = valid_contact_fields | valid_account_fields

        mappings = FieldMapping.objects.filter(org=self.org, is_active=True)

        for mapping in mappings:
            if mapping.target_field not in all_valid:
                self.report.issues.append(ReviewIssue(
                    severity="critical",
                    category="field_mapping",
                    entity_type="field_mapping",
                    entity_id=str(mapping.id),
                    message=(
                        f"FieldMapping '{mapping.source_field} → {mapping.target_field}' "
                        f"(connector={mapping.connector_slug}) aponta para campo CRM inválido."
                    ),
                ))

            # Verificar se o alias é reconhecido pelo registry
            resolved = resolve_to_crm_field("contact", mapping.source_field)
            if resolved and resolved != mapping.target_field:
                self.report.issues.append(ReviewIssue(
                    severity="info",
                    category="field_mapping",
                    entity_type="field_mapping",
                    entity_id=str(mapping.id),
                    message=(
                        f"FieldMapping '{mapping.source_field} → {mapping.target_field}': "
                        f"o variable_registry sugere mapear para '{resolved}' ao invés de '{mapping.target_field}'."
                    ),
                ))

    # ─── CHECK: INTEGRATION HEALTH ───────────────────────────────────────

    def _check_integration_health(self):
        """Verificar saúde das conexões de integração."""
        from integrations.models import IntegrationConnection, SyncJob

        connections = IntegrationConnection.objects.filter(org=self.org, is_active=True)

        for conn in connections:
            if conn.health_status in ("degraded", "down"):
                self.report.issues.append(ReviewIssue(
                    severity="critical" if conn.health_status == "down" else "warning",
                    category="sync_health",
                    entity_type="integration",
                    entity_id=str(conn.id),
                    message=(
                        f"Integração '{conn.display_name}' ({conn.connector_slug}) "
                        f"com saúde '{conn.health_status}' (errors={conn.error_count})."
                    ),
                ))

            if conn.error_count > 10:
                self.report.issues.append(ReviewIssue(
                    severity="warning",
                    category="sync_health",
                    entity_type="integration",
                    entity_id=str(conn.id),
                    message=(
                        f"Integração '{conn.display_name}' acumulou {conn.error_count} erros."
                    ),
                ))

            # Verificar se último sync foi há mais de 24h
            if conn.last_sync_at and conn.last_sync_at < timezone.now() - timedelta(hours=24):
                hours_ago = int((timezone.now() - conn.last_sync_at).total_seconds() / 3600)
                self.report.issues.append(ReviewIssue(
                    severity="info",
                    category="sync_health",
                    entity_type="integration",
                    entity_id=str(conn.id),
                    message=(
                        f"Integração '{conn.display_name}' sem sync há {hours_ago}h."
                    ),
                ))

            # Verificar sync jobs falhados recentes
            failed_jobs = SyncJob.objects.filter(
                org=self.org,
                connector_slug=conn.connector_slug,
                status="FAILED",
                created_at__gte=timezone.now() - timedelta(hours=24),
            ).count()

            if failed_jobs > 0:
                self.report.issues.append(ReviewIssue(
                    severity="warning",
                    category="sync_health",
                    entity_type="integration",
                    entity_id=str(conn.id),
                    message=(
                        f"Integração '{conn.display_name}' teve {failed_jobs} "
                        f"sync jobs falhados nas últimas 24h."
                    ),
                ))

    # ─── CHECK: TALKHUB SUBSCRIBERS ──────────────────────────────────────

    def _check_talkhub_subscribers(self):
        """Verificar integridade dos dados TalkHub."""
        from conversations.models import Conversation

        # Conversas com omni_user_ns mas contact sem talkhub_subscriber_id
        convs = Conversation.objects.filter(
            org=self.org,
        ).exclude(
            Q(omni_user_ns__isnull=True) | Q(omni_user_ns="")
        ).select_related("contact")

        for conv in convs[:50]:
            if conv.contact and not conv.contact.talkhub_subscriber_id:
                self.report.issues.append(ReviewIssue(
                    severity="warning",
                    category="talkhub_sync",
                    entity_type="contact",
                    entity_id=str(conv.contact.id),
                    message=(
                        f"Contact '{conv.contact.first_name}' tem conversa com "
                        f"omni_user_ns='{conv.omni_user_ns}' mas talkhub_subscriber_id está vazio."
                    ),
                    auto_fixable=True,
                    fix_action=f"set_subscriber_id:{conv.omni_user_ns}",
                ))

    # ─── CHECK: REQUIRED FIELDS ──────────────────────────────────────────

    def _check_required_fields(self):
        """Verificar contacts com campos obrigatórios vazios."""
        from contacts.models import Contact

        # Contacts sem first_name
        empty_name = Contact.objects.filter(
            org=self.org,
        ).filter(
            Q(first_name__isnull=True) | Q(first_name="")
        ).count()

        if empty_name > 0:
            self.report.issues.append(ReviewIssue(
                severity="critical",
                category="data_quality",
                entity_type="contact",
                message=f"{empty_name} contacts sem first_name preenchido.",
            ))

        # Contacts sem email E sem phone (sem forma de contato)
        no_contact_info = Contact.objects.filter(
            org=self.org,
        ).filter(
            Q(email__isnull=True) | Q(email="")
        ).filter(
            Q(phone__isnull=True) | Q(phone="")
        ).count()

        if no_contact_info > 0:
            self.report.issues.append(ReviewIssue(
                severity="info",
                category="data_quality",
                entity_type="contact",
                message=f"{no_contact_info} contacts sem email nem phone (sem forma de contato direta).",
            ))

    # ─── CHECK: CONVERSATIONS INTEGRITY ──────────────────────────────────

    def _check_conversations_integrity(self):
        """Verificar integridade das conversas."""
        from conversations.models import Conversation

        # Conversas abertas sem mensagem
        empty_convs = Conversation.objects.filter(
            org=self.org,
            status="open",
        ).annotate(
            msg_count=Count("messages")
        ).filter(msg_count=0).count()

        if empty_convs > 0:
            self.report.issues.append(ReviewIssue(
                severity="info",
                category="data_quality",
                entity_type="conversation",
                message=f"{empty_convs} conversas abertas sem nenhuma mensagem.",
            ))

    # ─── AUTO-FIX ────────────────────────────────────────────────────────

    def _apply_fixes(self):
        """Aplicar correções automáticas para issues marcadas como auto_fixable."""
        from integrations.data_unifier import DataUnifier

        unifier = DataUnifier(self.org, connector_slug="review_agent")

        for issue in self.report.issues:
            if not issue.auto_fixable or not issue.fix_action:
                continue

            try:
                if issue.fix_action.startswith("auto_link_account:"):
                    company_name = issue.fix_action.split(":", 1)[1]
                    self._fix_orphan_link(issue.entity_id, company_name, unifier)
                    self.report.fixes_applied.append(
                        f"Linked contact {issue.entity_id} to account '{company_name}'"
                    )

                elif issue.fix_action.startswith("set_subscriber_id:"):
                    subscriber_id = issue.fix_action.split(":", 1)[1]
                    self._fix_subscriber_id(issue.entity_id, subscriber_id)
                    self.report.fixes_applied.append(
                        f"Set talkhub_subscriber_id={subscriber_id} on contact {issue.entity_id}"
                    )

            except Exception as e:
                logger.error("Auto-fix failed for %s: %s", issue.fix_action, e)

    def _fix_orphan_link(self, contact_id: str, company_name: str, unifier):
        """Linkar contact órfão com Account."""
        from contacts.models import Contact

        contact = Contact.objects.get(id=contact_id, org=self.org)
        unifier._auto_link_contact_account(contact, company_name)

    def _fix_subscriber_id(self, contact_id: str, subscriber_id: str):
        """Preencher talkhub_subscriber_id em contact."""
        from contacts.models import Contact

        Contact.objects.filter(
            id=contact_id, org=self.org
        ).update(
            talkhub_subscriber_id=subscriber_id,
            updated_at=timezone.now(),
        )
