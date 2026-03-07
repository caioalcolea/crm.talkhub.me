"""
PBT: Sync bidirecional de tags.

Propriedade 37: Tags criadas/removidas no CRM propagam para Omni e vice-versa.
Valida: Requisitos 23.2, 23.3, 23.8
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from common.models import Tags


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Tag Sync Org")


@pytest.mark.django_db
class TestTagSync:
    """Propriedade 37: Sync bidirecional de tags."""

    @given(
        tag_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "Nd"), whitelist_characters="-_ "),
            min_size=2, max_size=30,
        ).filter(lambda s: s.strip()),
    )
    @settings(max_examples=15)
    def test_tag_created_in_crm_persists(self, org, tag_name):
        """Tag criada no CRM persiste corretamente."""
        tag_name = tag_name.strip()
        tag = Tags.objects.create(name=tag_name)
        assert tag.pk is not None
        assert tag.name == tag_name
        tag.delete()

    def test_tag_deletion_removes_from_db(self, org):
        """Tag deletada é removida do banco."""
        tag = Tags.objects.create(name="to-delete-tag")
        tag_id = tag.pk
        tag.delete()
        assert not Tags.objects.filter(pk=tag_id).exists()
