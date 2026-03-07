"""
PBT: Validação de registro de conectores no ConnectorRegistry.

Propriedade 1: Classes sem métodos obrigatórios falham com TypeError.
              Classes com todos os métodos são acessíveis via get(slug).
Valida: Requisitos 2.1, 2.3
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.registry import ConnectorRegistry


REQUIRED_METHODS = [
    "connect", "disconnect", "sync",
    "get_status", "get_health", "get_config_schema", "handle_webhook",
]


def _make_connector_class(slug, methods_to_include):
    """Dynamically create a connector class with specified methods."""
    attrs = {"slug": slug}
    for m in methods_to_include:
        attrs[m] = lambda self: None
    return type(f"Connector_{slug}", (), attrs)


@given(
    slug=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        min_size=3,
        max_size=30,
    ).filter(lambda s: s[0].isalpha()),
)
@settings(max_examples=30)
def test_valid_connector_registers_and_is_retrievable(slug):
    """Conector com todos os métodos obrigatórios registra e é acessível via get()."""
    # Limpar registry para isolamento
    ConnectorRegistry._connectors = {}

    cls = _make_connector_class(slug, REQUIRED_METHODS)
    ConnectorRegistry.register(cls)

    assert ConnectorRegistry.get(slug) is cls
    assert slug in ConnectorRegistry.all()


@given(
    slug=st.text(
        alphabet=st.characters(whitelist_categories=("Ll",), whitelist_characters="-"),
        min_size=3,
        max_size=20,
    ).filter(lambda s: s[0].isalpha()),
    missing_idx=st.integers(min_value=0, max_value=len(REQUIRED_METHODS) - 1),
)
@settings(max_examples=30)
def test_incomplete_connector_raises_type_error(slug, missing_idx):
    """Conector sem algum método obrigatório falha com TypeError."""
    ConnectorRegistry._connectors = {}

    partial_methods = [m for i, m in enumerate(REQUIRED_METHODS) if i != missing_idx]
    cls = _make_connector_class(slug, partial_methods)

    with pytest.raises(TypeError):
        ConnectorRegistry.register(cls)


def test_connector_without_slug_raises_type_error():
    """Conector sem atributo slug falha com TypeError."""
    ConnectorRegistry._connectors = {}

    attrs = {m: lambda self: None for m in REQUIRED_METHODS}
    cls = type("NoSlugConnector", (), attrs)

    with pytest.raises(TypeError):
        ConnectorRegistry.register(cls)
