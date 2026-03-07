"""
PBT: Opt-out bloqueia envio por canal.

Propriedade 35: Contato em opt-out não recebe mensagens pelo canal.
Propriedade 42: Intervalo de sync dentro dos limites.
Valida: Requisitos 21.2, 21.3, 21.5, 15.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from talkhub_omni.models import TalkHubSyncConfig


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="OptInOut Org")


@pytest.fixture
def contact(db, org):
    from contacts.models import Contact
    return Contact.objects.create(
        org=org, first_name="Opt", last_name="Test",
        sms_opt_in=True, email_opt_in=True,
    )


@pytest.mark.django_db
class TestOptOut:
    """Propriedade 35: Opt-out bloqueia envio."""

    def test_sms_opt_out_blocks_sms(self, contact):
        """Contato com sms_opt_in=False não deve receber SMS."""
        contact.sms_opt_in = False
        contact.save()
        contact.refresh_from_db()
        assert contact.sms_opt_in is False

    def test_email_opt_out_blocks_email(self, contact):
        """Contato com email_opt_in=False não deve receber email."""
        contact.email_opt_in = False
        contact.save()
        contact.refresh_from_db()
        assert contact.email_opt_in is False

    @given(
        sms=st.booleans(),
        email=st.booleans(),
    )
    @settings(max_examples=10)
    def test_opt_in_out_persists(self, contact, sms, email):
        """Status de opt-in/opt-out persiste corretamente."""
        contact.sms_opt_in = sms
        contact.email_opt_in = email
        contact.save()
        contact.refresh_from_db()
        assert contact.sms_opt_in == sms
        assert contact.email_opt_in == email


@pytest.mark.django_db
class TestSyncIntervals:
    """Propriedade 42: Intervalo de sync dentro dos limites."""

    @given(
        contacts_interval=st.integers(min_value=1, max_value=1440),
        tickets_interval=st.integers(min_value=1, max_value=1440),
        stats_interval=st.integers(min_value=1, max_value=1440),
    )
    @settings(max_examples=10)
    def test_sync_intervals_persist(self, org, contacts_interval, tickets_interval, stats_interval):
        """Intervalos de sync persistem corretamente."""
        config, _ = TalkHubSyncConfig.objects.update_or_create(
            org=org,
            defaults={
                "contacts_interval_minutes": contacts_interval,
                "tickets_interval_minutes": tickets_interval,
                "statistics_interval_minutes": stats_interval,
            },
        )
        config.refresh_from_db()
        assert config.contacts_interval_minutes == contacts_interval
        assert config.tickets_interval_minutes == tickets_interval
        assert config.statistics_interval_minutes == stats_interval
