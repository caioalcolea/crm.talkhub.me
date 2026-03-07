"""
Bug Condition Exploration Test — CommentView POST ausente em 4 entidades.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 1 (Fault Condition): POST para Account, Task, Opportunity e Case
CommentViews deve retornar HTTP 200 e criar um Comment via ContentType.

Este teste codifica o comportamento ESPERADO (correto). Quando executado no
código NÃO-CORRIGIDO, ele FALHARÁ (HTTP 405 em vez de 200), confirmando
que o bug existe.
"""

import uuid

import pytest

from accounts.models import Account
from cases.models import Case
from opportunity.models import Opportunity
from tasks.models import Task


# ---------------------------------------------------------------------------
# Fixtures — entidades de teste
# ---------------------------------------------------------------------------

@pytest.fixture
def account(org_a):
    return Account.objects.create(name="Test Account", org=org_a)


@pytest.fixture
def task(org_a):
    return Task.objects.create(
        title="Test Task", status="New", priority="Medium", org=org_a,
    )


@pytest.fixture
def opportunity(org_a):
    return Opportunity.objects.create(
        name="Test Opp", stage="PROSPECTING", org=org_a,
    )


@pytest.fixture
def case(org_a):
    return Case.objects.create(
        name="Test Case", status="New", priority="Low", org=org_a,
    )


# ---------------------------------------------------------------------------
# Endpoint map
# ---------------------------------------------------------------------------

ENTITY_ENDPOINTS = {
    "account": "/api/accounts/comment/{pk}/",
    "task": "/api/tasks/comment/{pk}/",
    "opportunity": "/api/opportunities/comment/{pk}/",
    "case": "/api/cases/comment/{pk}/",
}


# ---------------------------------------------------------------------------
# Property 1: POST com comment válido → HTTP 200 + payload correto
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCommentPostCreatesComment:
    """POST com comment válido deve retornar HTTP 200 e criar Comment."""

    def _post_comment(self, client, url, text="Test comment"):
        return client.post(url, {"comment": text}, format="json")

    def test_account_comment_post(self, admin_client, account):
        url = ENTITY_ENDPOINTS["account"].format(pk=account.pk)
        resp = self._post_comment(admin_client, url)
        assert resp.status_code == 200, (
            f"Account POST returned {resp.status_code}, expected 200"
        )
        data = resp.json()
        assert "id" in data
        assert data["comment"] == "Test comment"
        assert "commented_on" in data
        assert "commented_by" in data

    def test_task_comment_post(self, admin_client, task):
        url = ENTITY_ENDPOINTS["task"].format(pk=task.pk)
        resp = self._post_comment(admin_client, url)
        assert resp.status_code == 200, (
            f"Task POST returned {resp.status_code}, expected 200"
        )
        data = resp.json()
        assert "id" in data
        assert data["comment"] == "Test comment"
        assert "commented_on" in data
        assert "commented_by" in data

    def test_opportunity_comment_post(self, admin_client, opportunity):
        url = ENTITY_ENDPOINTS["opportunity"].format(pk=opportunity.pk)
        resp = self._post_comment(admin_client, url)
        assert resp.status_code == 200, (
            f"Opportunity POST returned {resp.status_code}, expected 200"
        )
        data = resp.json()
        assert "id" in data
        assert data["comment"] == "Test comment"
        assert "commented_on" in data
        assert "commented_by" in data

    def test_case_comment_post(self, admin_client, case):
        url = ENTITY_ENDPOINTS["case"].format(pk=case.pk)
        resp = self._post_comment(admin_client, url)
        assert resp.status_code == 200, (
            f"Case POST returned {resp.status_code}, expected 200"
        )
        data = resp.json()
        assert "id" in data
        assert data["comment"] == "Test comment"
        assert "commented_on" in data
        assert "commented_by" in data


# ---------------------------------------------------------------------------
# Property 2: POST com comment vazio → HTTP 400
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCommentPostEmptyValidation:
    """POST com comment vazio deve retornar HTTP 400."""

    def test_account_empty_comment(self, admin_client, account):
        url = ENTITY_ENDPOINTS["account"].format(pk=account.pk)
        resp = admin_client.post(url, {"comment": ""}, format="json")
        assert resp.status_code == 400

    def test_task_empty_comment(self, admin_client, task):
        url = ENTITY_ENDPOINTS["task"].format(pk=task.pk)
        resp = admin_client.post(url, {"comment": ""}, format="json")
        assert resp.status_code == 400

    def test_opportunity_empty_comment(self, admin_client, opportunity):
        url = ENTITY_ENDPOINTS["opportunity"].format(pk=opportunity.pk)
        resp = admin_client.post(url, {"comment": ""}, format="json")
        assert resp.status_code == 400

    def test_case_empty_comment(self, admin_client, case):
        url = ENTITY_ENDPOINTS["case"].format(pk=case.pk)
        resp = admin_client.post(url, {"comment": ""}, format="json")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Property 3: POST com pk inexistente → HTTP 404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCommentPostNotFound:
    """POST com pk inexistente deve retornar HTTP 404."""

    def test_account_not_found(self, admin_client):
        url = ENTITY_ENDPOINTS["account"].format(pk=uuid.uuid4())
        resp = admin_client.post(url, {"comment": "test"}, format="json")
        assert resp.status_code == 404

    def test_task_not_found(self, admin_client):
        url = ENTITY_ENDPOINTS["task"].format(pk=uuid.uuid4())
        resp = admin_client.post(url, {"comment": "test"}, format="json")
        assert resp.status_code == 404

    def test_opportunity_not_found(self, admin_client):
        url = ENTITY_ENDPOINTS["opportunity"].format(pk=uuid.uuid4())
        resp = admin_client.post(url, {"comment": "test"}, format="json")
        assert resp.status_code == 404

    def test_case_not_found(self, admin_client):
        url = ENTITY_ENDPOINTS["case"].format(pk=uuid.uuid4())
        resp = admin_client.post(url, {"comment": "test"}, format="json")
        assert resp.status_code == 404


# PBT tests removed — hypothesis + Django DB fixtures cause hangs on Windows.
# The 12 deterministic tests above cover the bug condition thoroughly.
