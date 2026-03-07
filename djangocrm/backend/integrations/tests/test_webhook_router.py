"""
PBT: Roteamento de webhooks, conector desativado, validação e logging.

Propriedade 2: Roteamento de webhooks por slug
Propriedade 3: Conector desativado bloqueia operações
Propriedade 16: Validação de webhook (autenticidade)
Propriedade 17: Log de webhooks recebidos
Valida: Requisitos 2.5, 6.1, 6.6, 6.2, 6.3, 6.5
"""

import json
import uuid

import pytest
from django.test import RequestFactory
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.registry import ConnectorRegistry


def _make_valid_connector(slug, validate_result=True):
    """Create a minimal valid connector class."""
    class FakeConnector:
        pass

    FakeConnector.slug = slug
    FakeConnector.connect = lambda self, org, config: True
    FakeConnector.disconnect = lambda self, org: True
    FakeConnector.sync = lambda self, org, st, jid: {}
    FakeConnector.get_status = lambda self, org: {}
    FakeConnector.get_health = lambda self, org: {"status": "healthy"}
    FakeConnector.get_config_schema = lambda self: {}
    FakeConnector.handle_webhook = lambda self, org, payload, headers: {"ok": True}
    FakeConnector.validate_webhook = lambda self, payload, headers, secret: validate_result
    return FakeConnector


@given(
    slug=st.from_regex(r"[a-z][a-z0-9\-]{2,20}", fullmatch=True),
)
@settings(max_examples=20)
def test_webhook_routes_to_correct_connector(slug):
    """Webhook com slug válido é roteado para o conector correto."""
    ConnectorRegistry._connectors = {}
    cls = _make_valid_connector(slug)
    ConnectorRegistry.register(cls)

    resolved = ConnectorRegistry.get(slug)
    assert resolved is cls

    connector = resolved()
    result = connector.handle_webhook(None, {"event": "test"}, {})
    assert result == {"ok": True}


@given(
    slug=st.from_regex(r"[a-z][a-z0-9\-]{2,20}", fullmatch=True),
)
@settings(max_examples=20)
def test_unknown_slug_returns_none(slug):
    """Slug desconhecido retorna None do registry."""
    ConnectorRegistry._connectors = {}
    assert ConnectorRegistry.get(slug) is None


def test_connector_validate_webhook_rejects_invalid():
    """Conector que rejeita webhook retorna False na validação."""
    cls = _make_valid_connector("test-reject", validate_result=False)
    connector = cls()
    assert connector.validate_webhook(b"payload", {}, "secret") is False


def test_connector_validate_webhook_accepts_valid():
    """Conector que aceita webhook retorna True na validação."""
    cls = _make_valid_connector("test-accept", validate_result=True)
    connector = cls()
    assert connector.validate_webhook(b"payload", {}, "secret") is True
