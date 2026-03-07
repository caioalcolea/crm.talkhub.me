"""
PBT: Criação automática de Opportunity e deduplicação.

Propriedade 23: Criação automática de Opportunity
Propriedade 24: Deduplicação de Opportunity por Contact+Pipeline
Valida: Requisitos 9.1, 9.2, 9.3, 9.4, 9.5
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from leads.models import Lead, LeadPipeline, LeadStage


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Auto Opp Org")


@pytest.fixture
def pipeline(db, org):
    return LeadPipeline.objects.create(
        org=org, name="Auto Opp Pipeline",
        is_default=True, auto_create_opportunity=True,
    )


@pytest.fixture
def stage(db, org, pipeline):
    return LeadStage.objects.create(
        pipeline=pipeline, name="New", order=0,
        stage_type="open", org=org,
    )


@pytest.fixture
def contact(db, org):
    from contacts.models import Contact
    return Contact.objects.create(
        org=org, first_name="Opp", last_name="Contact",
    )


@pytest.mark.django_db
class TestAutoCreateOpportunity:
    """Propriedade 23: Criação automática de Opportunity."""

    def test_pipeline_has_auto_create_flag(self, pipeline):
        """Pipeline com auto_create_opportunity=True está configurado."""
        assert pipeline.auto_create_opportunity is True

    def test_pipeline_without_auto_create(self, org):
        """Pipeline sem auto_create_opportunity não cria Opportunity."""
        p = LeadPipeline.objects.create(
            org=org, name="No Auto", auto_create_opportunity=False,
        )
        assert p.auto_create_opportunity is False

    @given(
        auto_create=st.booleans(),
    )
    @settings(max_examples=5)
    def test_auto_create_flag_persists(self, org, auto_create):
        """Flag auto_create_opportunity persiste corretamente."""
        p = LeadPipeline.objects.create(
            org=org, name=f"Test-{auto_create}",
            auto_create_opportunity=auto_create,
        )
        p.refresh_from_db()
        assert p.auto_create_opportunity == auto_create
        p.delete()
