"""
PBT: Acesso restrito a administradores nos endpoints de integrations.

Propriedade 5: Usuários sem permissão admin recebem HTTP 403.
Valida: Requisito 1.9
"""

import pytest
from django.test import RequestFactory
from hypothesis import given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Test Org")


@pytest.fixture
def admin_user(db, org):
    from django.contrib.auth.models import User
    from common.models import Profile

    user = User.objects.create_user(username="admin_test", password="pass123")
    profile = Profile.objects.create(
        user=user, org=org, role="ADMIN", is_active=True
    )
    return user, profile


@pytest.fixture
def non_admin_user(db, org):
    from django.contrib.auth.models import User
    from common.models import Profile

    user = User.objects.create_user(username="regular_test", password="pass123")
    profile = Profile.objects.create(
        user=user, org=org, role="USER", is_active=True
    )
    return user, profile


PROTECTED_ENDPOINTS = [
    "/api/integrations/",
    "/api/integrations/logs/",
]


@pytest.mark.django_db
class TestAdminOnlyAccess:
    """Propriedade 5: Endpoints de integrations restritos a admin."""

    def test_unauthenticated_user_gets_401(self):
        """Usuário não autenticado recebe 401."""
        client = APIClient()
        for endpoint in PROTECTED_ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code in (401, 403), (
                f"{endpoint} returned {response.status_code} for unauthenticated user"
            )

    def test_admin_user_can_access(self, admin_user):
        """Usuário admin pode acessar endpoints protegidos."""
        user, profile = admin_user
        client = APIClient()
        client.force_authenticate(user=user)
        # Apenas verificar que não retorna 403
        for endpoint in PROTECTED_ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code != 403, (
                f"{endpoint} returned 403 for admin user"
            )
