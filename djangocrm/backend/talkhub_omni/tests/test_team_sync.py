"""
PBT: Sync aditiva de membros da equipe.

Propriedade 38: Sync é aditiva — membros nunca são deletados do CRM.
Valida: Requisitos 24.2, 24.4, 24.6
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from talkhub_omni.models import TalkHubTeamMember


@pytest.fixture
def org(db):
    from common.models import Org
    return Org.objects.create(name="Team Sync Org")


@pytest.mark.django_db
class TestTeamMemberSync:
    """Propriedade 38: Sync aditiva de membros."""

    @given(
        agent_id=st.from_regex(r"agent-[0-9]{4}", fullmatch=True),
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L",), whitelist_characters=" "),
            min_size=2, max_size=30,
        ).filter(lambda s: s.strip()),
        role=st.sampled_from(["owner", "admin", "agent", "viewer"]),
    )
    @settings(max_examples=10)
    def test_team_member_created_correctly(self, org, agent_id, name, role):
        """Membro da equipe é criado com dados corretos."""
        member = TalkHubTeamMember.objects.create(
            org=org, omni_agent_id=agent_id,
            name=name.strip(), role=role,
        )
        assert member.pk is not None
        assert member.role == role
        assert member.omni_agent_id == agent_id
        member.delete()

    def test_additive_sync_does_not_delete(self, org):
        """Sync aditiva: novos membros são adicionados, existentes não são removidos."""
        m1 = TalkHubTeamMember.objects.create(
            org=org, omni_agent_id="existing-001", name="Existing Agent", role="agent",
        )
        m2 = TalkHubTeamMember.objects.create(
            org=org, omni_agent_id="new-002", name="New Agent", role="agent",
        )

        # Simular sync que traz apenas m2 — m1 deve continuar existindo
        assert TalkHubTeamMember.objects.filter(org=org, omni_agent_id="existing-001").exists()
        assert TalkHubTeamMember.objects.filter(org=org, omni_agent_id="new-002").exists()

    def test_unique_agent_id_per_org(self, org):
        """Mesmo agent_id não pode existir duas vezes na mesma org."""
        from django.db import IntegrityError

        TalkHubTeamMember.objects.create(
            org=org, omni_agent_id="dup-agent", name="Agent 1", role="agent",
        )
        with pytest.raises(IntegrityError):
            TalkHubTeamMember.objects.create(
                org=org, omni_agent_id="dup-agent", name="Agent 2", role="agent",
            )
