"""
PBT: Retenção de logs de 90 dias e persistência de integração.

Propriedade 29: cleanup_old_logs remove logs > 90 dias e preserva recentes.
Propriedade 6: Persistência de integração com campos obrigatórios.
Valida: Requisitos 12.3, 1.10
"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.models import IntegrationConnection, IntegrationLog, WebhookLog


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Test Org")


@pytest.mark.django_db
class TestLogRetention:
    """Propriedade 29: Retenção de logs de 90 dias."""

    @given(
        days_old=st.integers(min_value=91, max_value=365),
    )
    @settings(max_examples=10)
    def test_old_logs_are_deleted(self, org, days_old):
        """Logs com mais de 90 dias são removidos pelo cleanup."""
        from integrations.tasks import cleanup_old_logs

        old_date = timezone.now() - timedelta(days=days_old)

        log = IntegrationLog.objects.create(
            org=org,
            connector_slug="test",
            operation="sync",
            direction="in",
            entity_type="contact",
            status="success",
        )
        IntegrationLog.objects.filter(pk=log.pk).update(created_at=old_date)

        wlog = WebhookLog.objects.create(
            org=org,
            connector_slug="test",
            event_type="subscriber.created",
        )
        WebhookLog.objects.filter(pk=wlog.pk).update(created_at=old_date)

        result = cleanup_old_logs()

        assert result["deleted_logs"] >= 1
        assert result["deleted_webhooks"] >= 1

    @given(
        days_old=st.integers(min_value=0, max_value=89),
    )
    @settings(max_examples=10)
    def test_recent_logs_are_preserved(self, org, days_old):
        """Logs com menos de 90 dias são preservados."""
        from integrations.tasks import cleanup_old_logs

        recent_date = timezone.now() - timedelta(days=days_old)

        log = IntegrationLog.objects.create(
            org=org,
            connector_slug="test",
            operation="sync",
            direction="in",
            entity_type="contact",
            status="success",
        )
        IntegrationLog.objects.filter(pk=log.pk).update(created_at=recent_date)

        cleanup_old_logs()

        assert IntegrationLog.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
class TestIntegrationPersistence:
    """Propriedade 6: Persistência de integração com campos obrigatórios."""

    @given(
        slug=st.from_regex(r"[a-z][a-z0-9\-]{2,20}", fullmatch=True),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    @settings(max_examples=10)
    def test_integration_connection_requires_org_and_slug(self, org, slug, display_name):
        """IntegrationConnection requer org e connector_slug."""
        conn = IntegrationConnection.objects.create(
            org=org,
            connector_slug=slug,
            display_name=display_name.strip(),
        )
        assert conn.pk is not None
        assert conn.org == org
        assert conn.connector_slug == slug
        assert conn.health_status == "unknown"
        assert conn.conflict_strategy == "last_write_wins"

        # Cleanup
        conn.delete()
