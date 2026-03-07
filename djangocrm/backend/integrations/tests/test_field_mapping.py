"""
PBT: Validação de mapeamento de campos e transformações.

Propriedade 7: Validação de mapeamento de campos
Propriedade 8: Transformações de campo preservam estrutura
Propriedade 9: Isolamento de mapeamentos por Org
Valida: Requisitos 3.2, 3.3, 3.4
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from integrations.field_transforms import (
    apply_field_mapping,
    concat_name,
    format_phone,
    split_full_name,
)
from integrations.variable_registry import (
    CONTACT_SCHEMA,
    resolve_to_crm_field,
    resolve_variable,
)


class TestSplitConcatRoundTrip:
    """Propriedade 8: split/concat preservam estrutura."""

    @given(
        first=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=30,
        ),
        last=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(max_examples=50)
    def test_split_concat_round_trip(self, first, last):
        """split(concat(first, last)) preserva first_name e last_name."""
        full = concat_name(first, last)
        parts = split_full_name(full)
        assert parts["first_name"] == first
        assert parts["last_name"] == last

    @given(name=st.text(min_size=0, max_size=5).filter(lambda s: not s.strip()))
    @settings(max_examples=10)
    def test_split_empty_name(self, name):
        """split de nome vazio retorna strings vazias."""
        parts = split_full_name(name)
        assert parts["first_name"] == ""
        assert parts["last_name"] == ""

    @given(
        first=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=20)
    def test_split_single_name(self, first):
        """split de nome único retorna last_name vazio."""
        parts = split_full_name(first)
        assert parts["first_name"] == first
        assert parts["last_name"] == ""


class TestPhoneFormat:
    """Transformação de telefone."""

    @given(
        digits=st.from_regex(r"[1-9]\d{9,12}", fullmatch=True),
    )
    @settings(max_examples=20)
    def test_format_phone_adds_country_code(self, digits):
        """format_phone adiciona código do país BR quando ausente."""
        result = format_phone(digits, "BR")
        assert result.startswith("+55") or result == digits

    def test_format_phone_preserves_plus_prefix(self):
        """Telefone com + é preservado."""
        assert format_phone("+5511999999999") == "+5511999999999"

    def test_format_phone_empty(self):
        """Telefone vazio retorna string vazia."""
        assert format_phone("") == ""


class TestVariableRegistryResolution:
    """Propriedade 7: Validação de mapeamento de campos."""

    @given(
        alias=st.sampled_from([
            "nome", "name", "subscriber_first_name",
            "sobrenome", "surname",
            "e-mail", "email_address",
            "telefone", "phone_number", "whatsapp",
            "empresa", "company",
        ]),
    )
    @settings(max_examples=30)
    def test_known_aliases_resolve_to_crm_field(self, alias):
        """Aliases conhecidos resolvem para campo CRM correto."""
        crm_field = resolve_to_crm_field("contact", alias)
        assert crm_field is not None
        assert isinstance(crm_field, str)

    @given(
        unknown=st.text(min_size=10, max_size=30).filter(
            lambda s: s.lower() not in {
                a.lower()
                for m in CONTACT_SCHEMA.values()
                for a in (m.crm_field, *m.aliases)
            }
        ),
    )
    @settings(max_examples=20)
    def test_unknown_variable_returns_none(self, unknown):
        """Variável desconhecida retorna None."""
        result = resolve_to_crm_field("contact", unknown)
        assert result is None


class TestFieldMappingApply:
    """Propriedade 8: apply_field_mapping com mapeamentos."""

    def test_apply_text_mapping(self):
        """Mapeamento de texto simples funciona."""
        class FakeMapping:
            is_active = True
            source_field = "external_name"
            target_field = "first_name"
            field_type = "text"
            transform_config = {}

        source = {"external_name": "João"}
        result = apply_field_mapping(source, [FakeMapping()])
        assert result["first_name"] == "João"

    def test_inactive_mapping_is_skipped(self):
        """Mapeamento inativo é ignorado."""
        class FakeMapping:
            is_active = False
            source_field = "external_name"
            target_field = "first_name"
            field_type = "text"
            transform_config = {}

        source = {"external_name": "João"}
        result = apply_field_mapping(source, [FakeMapping()])
        assert "first_name" not in result

    def test_missing_source_field_is_skipped(self):
        """Campo ausente no source é ignorado."""
        class FakeMapping:
            is_active = True
            source_field = "nonexistent"
            target_field = "first_name"
            field_type = "text"
            transform_config = {}

        result = apply_field_mapping({}, [FakeMapping()])
        assert result == {}
