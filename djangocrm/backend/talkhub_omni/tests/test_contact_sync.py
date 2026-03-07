"""
PBT: Sync bidirecional de contatos e anti-loop.

Propriedade 10: Sync bidirecional com correlação por subscriber_id
Propriedade 11: Anti-loop de sincronização (janela de 5 segundos)
Valida: Requisitos 4.1, 4.2, 4.3, 4.4, 4.5, 28.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.conflict_resolver import detect_conflict, set_sync_lock
from integrations.variable_registry import resolve_to_crm_field


class TestContactFieldMapping:
    """Propriedade 10: Mapeamento de campos subscriber → Contact."""

    @given(
        field_name=st.sampled_from([
            "subscriber_name", "subscriber_email", "subscriber_phone",
            "nome", "e-mail", "telefone", "whatsapp",
            "user_ns", "subscriber_id",
        ]),
    )
    @settings(max_examples=20)
    def test_subscriber_fields_resolve_to_crm_fields(self, field_name):
        """Campos de subscriber resolvem para campos CRM via variable_registry."""
        crm_field = resolve_to_crm_field("contact", field_name)
        assert crm_field is not None, f"Field '{field_name}' should resolve to a CRM field"

    @given(
        first=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1, max_size=20,
        ),
        last=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1, max_size=20,
        ),
        email=st.emails(),
    )
    @settings(max_examples=15)
    def test_contact_data_maps_correctly(self, first, last, email):
        """Dados de contato mapeiam para campos CRM corretos."""
        assert resolve_to_crm_field("contact", "first_name") == "first_name"
        assert resolve_to_crm_field("contact", "last_name") == "last_name"
        assert resolve_to_crm_field("contact", "email") == "email"


class TestAntiLoop:
    """Propriedade 11: Anti-loop de sincronização."""

    @given(
        entity_id=st.from_regex(r"[a-z0-9]{8,16}", fullmatch=True),
        org_id=st.from_regex(r"[a-z0-9]{8,16}", fullmatch=True),
    )
    @settings(max_examples=15)
    def test_sync_lock_prevents_echo(self, entity_id, org_id):
        """Sync lock ativo impede processamento de webhook eco."""
        set_sync_lock(entity_id, org_id, ttl=5)
        assert detect_conflict(entity_id, org_id) is True

    @given(
        entity_id=st.from_regex(r"unique-[a-z0-9]{8}", fullmatch=True),
        org_id=st.from_regex(r"unique-[a-z0-9]{8}", fullmatch=True),
    )
    @settings(max_examples=15)
    def test_no_lock_allows_processing(self, entity_id, org_id):
        """Sem sync lock, webhook é processado normalmente."""
        assert detect_conflict(entity_id, org_id) is False
