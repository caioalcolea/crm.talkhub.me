"""
PBT: Métricas filtradas por período.

Propriedade 44: Filtros de período retornam apenas dados do período solicitado.
Valida: Requisito 26.8
"""

import pytest
from datetime import timedelta

from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from talkhub_omni.models import OmniStatisticsSnapshot


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Metrics Test Org")


@pytest.mark.django_db
class TestMetricsByPeriod:
    """Propriedade 44: Métricas filtradas por período."""

    @given(
        period=st.sampled_from(["hourly", "daily", "weekly", "monthly"]),
        bot_users=st.integers(min_value=0, max_value=10000),
        messages=st.integers(min_value=0, max_value=50000),
    )
    @settings(max_examples=10)
    def test_snapshot_persists_with_period(self, org, period, bot_users, messages):
        """Snapshot de métricas persiste com período correto."""
        snap = OmniStatisticsSnapshot.objects.create(
            org=org, period=period,
            bot_users_count=bot_users, messages_count=messages,
        )
        assert snap.period == period
        assert snap.bot_users_count == bot_users
        assert snap.messages_count == messages
        snap.delete()

    def test_filter_by_date_range(self, org):
        """Filtro por data retorna apenas snapshots do período."""
        now = timezone.now()

        old = OmniStatisticsSnapshot.objects.create(
            org=org, period="daily", bot_users_count=100,
        )
        OmniStatisticsSnapshot.objects.filter(pk=old.pk).update(
            created_at=now - timedelta(days=30),
        )

        recent = OmniStatisticsSnapshot.objects.create(
            org=org, period="daily", bot_users_count=200,
        )

        # Filtrar últimos 7 dias
        cutoff = now - timedelta(days=7)
        qs = OmniStatisticsSnapshot.objects.filter(
            org=org, created_at__gte=cutoff,
        )
        assert recent in qs
        assert old not in qs

    def test_filter_by_period_type(self, org):
        """Filtro por tipo de período retorna apenas matches."""
        OmniStatisticsSnapshot.objects.create(
            org=org, period="hourly", bot_users_count=10,
        )
        OmniStatisticsSnapshot.objects.create(
            org=org, period="daily", bot_users_count=100,
        )

        hourly = OmniStatisticsSnapshot.objects.filter(org=org, period="hourly")
        daily = OmniStatisticsSnapshot.objects.filter(org=org, period="daily")

        assert hourly.count() >= 1
        assert daily.count() >= 1
        assert all(s.period == "hourly" for s in hourly)
        assert all(s.period == "daily" for s in daily)
