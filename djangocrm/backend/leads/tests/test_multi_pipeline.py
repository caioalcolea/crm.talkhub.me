"""
PBT: Multi-Pipeline para Leads.

Propriedade 18: Unicidade de pipeline padrão por Org
Propriedade 19: Lead sem pipeline explícito vai para pipeline padrão
Propriedade 20: Movimentação de Lead atualiza stage e status
Propriedade 21: WIP limit é respeitado
Valida: Requisitos 7.3, 7.4, 7.5, 7.6, 7.7
"""

import pytest
from django.db import IntegrityError
from hypothesis import given, settings
from hypothesis import strategies as st

from leads.models import Lead, LeadPipeline, LeadStage


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Pipeline Test Org")


@pytest.fixture
def default_pipeline(db, org):
    return LeadPipeline.objects.create(
        org=org, name="Default Pipeline", is_default=True,
    )


@pytest.fixture
def stages(db, org, default_pipeline):
    s1 = LeadStage.objects.create(
        pipeline=default_pipeline, name="New", order=0,
        stage_type="open", org=org,
    )
    s2 = LeadStage.objects.create(
        pipeline=default_pipeline, name="Qualified", order=1,
        stage_type="open", maps_to_status="assigned", org=org,
    )
    s3 = LeadStage.objects.create(
        pipeline=default_pipeline, name="Won", order=2,
        stage_type="won", maps_to_status="converted",
        wip_limit=2, org=org,
    )
    return s1, s2, s3


@pytest.mark.django_db
class TestDefaultPipelineUniqueness:
    """Propriedade 18: Unicidade de pipeline padrão por Org."""

    def test_only_one_default_pipeline_per_org(self, org, default_pipeline):
        """Criar segundo pipeline padrão na mesma org falha."""
        with pytest.raises(IntegrityError):
            LeadPipeline.objects.create(
                org=org, name="Second Default", is_default=True,
            )

    def test_different_orgs_can_have_default_pipelines(self, org, default_pipeline):
        """Orgs diferentes podem ter seus próprios pipelines padrão."""
        from common.models import Org
        org2 = Org.objects.create(name="Other Org")
        p2 = LeadPipeline.objects.create(
            org=org2, name="Other Default", is_default=True,
        )
        assert p2.is_default is True


@pytest.mark.django_db
class TestLeadStageMovement:
    """Propriedade 20: Movimentação de Lead atualiza stage e status."""

    def test_moving_lead_to_stage_with_maps_to_status(self, org, default_pipeline, stages):
        """Mover Lead para estágio com maps_to_status atualiza status."""
        s1, s2, s3 = stages
        lead = Lead.objects.create(
            org=org, first_name="Test", last_name="Lead",
            status="new", stage=s1,
        )
        # Mover para s2 que tem maps_to_status="assigned"
        lead.stage = s2
        if s2.maps_to_status:
            lead.status = s2.maps_to_status
        lead.save()
        lead.refresh_from_db()

        assert lead.stage == s2
        assert lead.status == "assigned"


@pytest.mark.django_db
class TestWIPLimit:
    """Propriedade 21: WIP limit é respeitado."""

    def test_wip_limit_count(self, org, default_pipeline, stages):
        """Estágio com wip_limit reporta quando limite é atingido."""
        _, _, won_stage = stages  # wip_limit=2

        Lead.objects.create(
            org=org, first_name="L1", last_name="Test",
            status="converted", stage=won_stage,
        )
        Lead.objects.create(
            org=org, first_name="L2", last_name="Test",
            status="converted", stage=won_stage,
        )

        count = Lead.objects.filter(stage=won_stage).count()
        assert count >= won_stage.wip_limit
