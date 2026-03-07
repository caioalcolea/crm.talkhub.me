"""
PBT: Validação de entidade pai única em Task.

Propriedade 22: Definir mais de um campo pai falha com ValidationError.
Valida: Requisitos 8.3, 8.2
"""

import pytest
from django.core.exceptions import ValidationError
from hypothesis import given, settings
from hypothesis import strategies as st

from tasks.models import Task


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Task Link Org")


@pytest.fixture
def account(db, org):
    from accounts.models import Account
    return Account.objects.create(org=org, name="Test Account")


@pytest.fixture
def case(db, org):
    from cases.models import Case
    return Case.objects.create(
        org=org, name="Test Case", status="New", priority="Medium",
    )


@pytest.fixture
def lead(db, org):
    from leads.models import Lead
    return Lead.objects.create(
        org=org, first_name="Test", last_name="Lead", status="new",
    )


@pytest.mark.django_db
class TestSingleParentEntity:
    """Propriedade 22: Validação de entidade pai única."""

    def test_task_with_single_parent_is_valid(self, org, case):
        """Task com apenas um pai é válida."""
        task = Task(
            org=org, title="Valid Task", status="New",
            priority="Medium", case=case,
        )
        task.clean()  # Não deve levantar exceção

    def test_task_with_two_parents_raises_validation_error(self, org, account, case):
        """Task com dois pais levanta ValidationError."""
        task = Task(
            org=org, title="Invalid Task", status="New",
            priority="Medium", account=account, case=case,
        )
        with pytest.raises(ValidationError):
            task.clean()

    def test_task_with_three_parents_raises_validation_error(self, org, account, case, lead):
        """Task com três pais levanta ValidationError."""
        task = Task(
            org=org, title="Invalid Task", status="New",
            priority="Medium", account=account, case=case, lead=lead,
        )
        with pytest.raises(ValidationError):
            task.clean()

    def test_task_with_no_parent_is_valid(self, org):
        """Task sem pai é válida."""
        task = Task(
            org=org, title="Orphan Task", status="New", priority="Medium",
        )
        task.clean()  # Não deve levantar exceção

    @given(
        parent_combo=st.lists(
            st.sampled_from(["account", "opportunity", "case", "lead"]),
            min_size=2, max_size=4, unique=True,
        ),
    )
    @settings(max_examples=10)
    def test_multiple_parents_always_fail(self, org, account, case, lead, parent_combo):
        """Qualquer combinação de 2+ pais falha com ValidationError."""
        kwargs = {
            "org": org, "title": "Multi Parent", "status": "New", "priority": "Medium",
        }
        parent_map = {"account": account, "case": case, "lead": lead}
        for field in parent_combo:
            if field in parent_map:
                kwargs[field] = parent_map[field]

        # Só testar se pelo menos 2 pais reais foram setados
        set_count = sum(1 for f in ["account", "case", "lead"] if f in parent_combo)
        if set_count >= 2:
            task = Task(**kwargs)
            with pytest.raises(ValidationError):
                task.clean()
