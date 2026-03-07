"""
PBT: Resolução de conflitos last-write-wins.

Propriedade 28: Conflitos são resolvidos corretamente por cada estratégia
               e ConflictLog é criado.
Valida: Requisitos 11.1, 11.2, 11.4
"""

import pytest
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.conflict_resolver import (
    detect_conflict,
    log_conflict,
    resolve_conflict,
    set_sync_lock,
)


class TestResolveConflict:
    """Propriedade 28: Resolução de conflitos por estratégia."""

    @given(
        crm_val=st.text(min_size=1, max_size=50),
        ext_val=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_crm_wins_always_returns_crm_value(self, crm_val, ext_val):
        """Estratégia crm_wins sempre retorna valor do CRM."""
        value, resolved_by = resolve_conflict(crm_val, ext_val, "crm_wins")
        assert value == crm_val
        assert resolved_by == "crm"

    @given(
        crm_val=st.text(min_size=1, max_size=50),
        ext_val=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_external_wins_always_returns_external_value(self, crm_val, ext_val):
        """Estratégia external_wins sempre retorna valor externo."""
        value, resolved_by = resolve_conflict(crm_val, ext_val, "external_wins")
        assert value == ext_val
        assert resolved_by == "external"

    @given(
        crm_val=st.text(min_size=1, max_size=50),
        ext_val=st.text(min_size=1, max_size=50),
        crm_newer=st.booleans(),
    )
    @settings(max_examples=30)
    def test_last_write_wins_respects_timestamps(self, crm_val, ext_val, crm_newer):
        """Estratégia last_write_wins respeita timestamps."""
        now = timezone.now()
        if crm_newer:
            crm_ts = now
            ext_ts = now - timezone.timedelta(seconds=10)
        else:
            crm_ts = now - timezone.timedelta(seconds=10)
            ext_ts = now

        value, resolved_by = resolve_conflict(
            crm_val, ext_val, "last_write_wins",
            crm_updated_at=crm_ts, external_updated_at=ext_ts,
        )
        assert resolved_by == "last_write"
        if crm_newer:
            assert value == crm_val
        else:
            assert value == ext_val

    @given(
        crm_val=st.text(min_size=1, max_size=50),
        ext_val=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=10)
    def test_last_write_wins_no_timestamps_defaults_to_external(self, crm_val, ext_val):
        """Sem timestamps, last_write_wins retorna valor externo."""
        value, resolved_by = resolve_conflict(crm_val, ext_val, "last_write_wins")
        assert value == ext_val
        assert resolved_by == "last_write"


class TestSyncLock:
    """Anti-loop via sync lock."""

    def test_detect_conflict_without_lock(self):
        """Sem lock, detect_conflict retorna False."""
        assert detect_conflict("entity-999", "org-999") is False

    def test_detect_conflict_with_lock(self):
        """Com lock ativo, detect_conflict retorna True."""
        set_sync_lock("entity-lock-test", "org-lock-test", ttl=10)
        assert detect_conflict("entity-lock-test", "org-lock-test") is True


@pytest.mark.django_db
class TestConflictLog:
    """Log de conflitos é criado corretamente."""

    @pytest.fixture
    def org(self):
        from common.models import Org
        return Org.objects.create(name="Conflict Test Org")

    @given(
        strategy=st.sampled_from(["crm_wins", "external_wins", "last_write_wins"]),
    )
    @settings(max_examples=5)
    def test_log_conflict_creates_record(self, org, strategy):
        """log_conflict cria registro no banco."""
        from integrations.models import ConflictLog

        resolved_by = {"crm_wins": "crm", "external_wins": "external", "last_write_wins": "last_write"}[strategy]

        log_conflict(
            org=org,
            connector_slug="test-connector",
            entity_type="contact",
            entity_id="123",
            crm_value={"name": "CRM"},
            external_value={"name": "External"},
            resolved_by=resolved_by,
            fields_overwritten=["name"],
        )

        log = ConflictLog.objects.filter(org=org, entity_id="123").last()
        assert log is not None
        assert log.resolved_by == resolved_by
        assert log.fields_overwritten == ["name"]
