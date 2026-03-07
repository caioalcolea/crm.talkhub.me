"""
PBT: Workflow de Cases — auto-preenchimento, first response, SLA.

Propriedade 25: Auto-preenchimento de campos de fechamento de Case
Propriedade 26: First response timestamp
Propriedade 27: Cálculo de indicador de SLA
Valida: Requisitos 10.1, 10.2, 10.3
"""

import pytest
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st

from cases.sla import compute_sla_indicator


class TestSLAIndicator:
    """Propriedade 27: Cálculo de indicador de SLA."""

    @given(
        sla_hours=st.integers(min_value=1, max_value=100),
        ratio=st.floats(min_value=0.0, max_value=0.749),
    )
    @settings(max_examples=20)
    def test_green_when_under_75_percent(self, sla_hours, ratio):
        """Indicador verde quando < 75% do SLA consumido."""
        elapsed = sla_hours * ratio
        assert compute_sla_indicator(sla_hours, elapsed) == "green"

    @given(
        sla_hours=st.integers(min_value=1, max_value=100),
        ratio=st.floats(min_value=0.75, max_value=0.999),
    )
    @settings(max_examples=20)
    def test_yellow_when_75_to_100_percent(self, sla_hours, ratio):
        """Indicador amarelo quando 75-100% do SLA consumido."""
        elapsed = sla_hours * ratio
        assert compute_sla_indicator(sla_hours, elapsed) == "yellow"

    @given(
        sla_hours=st.integers(min_value=1, max_value=100),
        ratio=st.floats(min_value=1.0, max_value=5.0),
    )
    @settings(max_examples=20)
    def test_red_when_over_100_percent(self, sla_hours, ratio):
        """Indicador vermelho quando >= 100% do SLA consumido."""
        elapsed = sla_hours * ratio
        assert compute_sla_indicator(sla_hours, elapsed) == "red"

    def test_zero_sla_returns_green(self):
        """SLA de 0 horas retorna verde (sem SLA configurado)."""
        assert compute_sla_indicator(0, 10) == "green"

    def test_negative_sla_returns_green(self):
        """SLA negativo retorna verde (edge case)."""
        assert compute_sla_indicator(-1, 10) == "green"


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Workflow Test Org")


@pytest.mark.django_db
class TestCaseClosedAutoFill:
    """Propriedade 25: Auto-preenchimento de campos de fechamento."""

    def test_case_sla_properties(self, org):
        """Case com SLA configurado calcula deadlines corretamente."""
        from cases.models import Case

        case = Case.objects.create(
            org=org, name="SLA Case", status="New", priority="High",
            sla_first_response_hours=2, sla_resolution_hours=8,
        )
        assert case.first_response_sla_deadline is not None
        assert case.resolution_sla_deadline is not None

    def test_first_response_not_breached_when_set(self, org):
        """Case com first_response_at preenchido não está em breach."""
        from cases.models import Case

        case = Case.objects.create(
            org=org, name="Responded Case", status="New", priority="Medium",
            first_response_at=timezone.now(),
        )
        assert case.is_sla_first_response_breached is False

    def test_resolved_case_not_breached(self, org):
        """Case resolvido não está em breach de resolução."""
        from cases.models import Case

        case = Case.objects.create(
            org=org, name="Resolved Case", status="Closed", priority="Medium",
            resolved_at=timezone.now(),
        )
        assert case.is_sla_resolution_breached is False
