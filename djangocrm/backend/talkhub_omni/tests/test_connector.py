"""
PBT: Saúde degradada após 3 falhas consecutivas.

Propriedade 4: get_health retorna "degraded" após 3 SyncJobs FAILED consecutivos.
Valida: Requisito 1.7
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from talkhub_omni.connector import TalkHubOmniConnector
from talkhub_omni.models import TalkHubSyncJob


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Health Test Org")


@pytest.mark.django_db
class TestConnectorHealth:
    """Propriedade 4: Saúde degradada após falhas."""

    @given(
        fail_count=st.integers(min_value=3, max_value=5),
    )
    @settings(max_examples=5)
    def test_degraded_after_consecutive_failures(self, org, fail_count):
        """get_health retorna 'degraded' após 3+ SyncJobs FAILED."""
        # Limpar jobs anteriores
        TalkHubSyncJob.objects.filter(org=org).delete()

        for _ in range(fail_count):
            TalkHubSyncJob.objects.create(
                org=org, sync_type="contacts", status="FAILED",
            )

        connector = TalkHubOmniConnector()
        health = connector.get_health(org)
        assert health["status"] == "degraded"
        assert health["error_count"] >= 3

    @given(
        success_count=st.integers(min_value=3, max_value=5),
    )
    @settings(max_examples=5)
    def test_healthy_with_all_successes(self, org, success_count):
        """get_health retorna 'healthy' com todos os jobs bem-sucedidos."""
        TalkHubSyncJob.objects.filter(org=org).delete()

        for _ in range(success_count):
            TalkHubSyncJob.objects.create(
                org=org, sync_type="contacts", status="COMPLETED",
            )

        connector = TalkHubOmniConnector()
        health = connector.get_health(org)
        assert health["status"] == "healthy"
        assert health["error_count"] == 0

    def test_warning_with_some_failures(self, org):
        """get_health retorna 'warning' com 1-2 falhas."""
        TalkHubSyncJob.objects.filter(org=org).delete()

        TalkHubSyncJob.objects.create(org=org, sync_type="contacts", status="FAILED")
        TalkHubSyncJob.objects.create(org=org, sync_type="contacts", status="COMPLETED")
        TalkHubSyncJob.objects.create(org=org, sync_type="contacts", status="COMPLETED")

        connector = TalkHubOmniConnector()
        health = connector.get_health(org)
        assert health["status"] == "warning"
        assert health["error_count"] == 1
