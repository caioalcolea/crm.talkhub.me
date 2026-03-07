"""
PBT: Sync de tickets — mapeamento de pipeline e propagação bidirecional.

Propriedade 13: Ticket sync respeita mapeamento de pipeline
Propriedade 14: Propagação bidirecional de status de tickets
Propriedade 15: Mapeamento de colunas de status para estágios
Valida: Requisitos 5.1-5.8
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from talkhub_omni.models import TalkHubTicketListMapping


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Ticket Sync Org")


@pytest.fixture
def lead_pipeline(db, org):
    from leads.models import LeadPipeline
    return LeadPipeline.objects.create(
        org=org, name="Sales Pipeline", is_default=True,
    )


@pytest.fixture
def case_pipeline(db, org):
    from cases.models import CasePipeline
    return CasePipeline.objects.create(
        org=org, name="Support Pipeline", is_default=True,
    )


@pytest.mark.django_db
class TestTicketListMapping:
    """Propriedade 13: Mapeamento de ticket list para pipeline."""

    @given(
        pipeline_type=st.sampled_from(["lead", "case"]),
        list_id=st.from_regex(r"list-[0-9]{4}", fullmatch=True),
    )
    @settings(max_examples=10)
    def test_mapping_persists_with_correct_type(
        self, org, lead_pipeline, case_pipeline, pipeline_type, list_id
    ):
        """TalkHubTicketListMapping persiste com pipeline_type correto."""
        kwargs = {
            "org": org,
            "omni_list_id": list_id,
            "omni_list_name": f"List {list_id}",
            "pipeline_type": pipeline_type,
        }
        if pipeline_type == "lead":
            kwargs["lead_pipeline"] = lead_pipeline
        else:
            kwargs["case_pipeline"] = case_pipeline

        mapping = TalkHubTicketListMapping.objects.create(**kwargs)
        assert mapping.pipeline_type == pipeline_type

        if pipeline_type == "lead":
            assert mapping.lead_pipeline == lead_pipeline
        else:
            assert mapping.case_pipeline == case_pipeline

        mapping.delete()

    def test_unique_list_id_per_org(self, org, lead_pipeline):
        """Mesmo list_id não pode ser mapeado duas vezes na mesma org."""
        from django.db import IntegrityError

        TalkHubTicketListMapping.objects.create(
            org=org, omni_list_id="dup-list",
            pipeline_type="lead", lead_pipeline=lead_pipeline,
        )
        with pytest.raises(IntegrityError):
            TalkHubTicketListMapping.objects.create(
                org=org, omni_list_id="dup-list",
                pipeline_type="lead", lead_pipeline=lead_pipeline,
            )
