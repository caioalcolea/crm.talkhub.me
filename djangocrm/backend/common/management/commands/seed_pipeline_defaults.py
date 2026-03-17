"""
Management command to seed default kanban pipelines for all 4 modules.

Usage:
    python manage.py seed_pipeline_defaults --all-orgs
    python manage.py seed_pipeline_defaults --org-id UUID
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from common.models import Org
from common.rls import get_set_context_sql


# Default pipeline stage definitions (pt-BR) per module
LEAD_STAGES = [
    {"name": "Novo", "order": 1, "color": "#3B82F6", "stage_type": "open", "maps_to_status": "assigned"},
    {"name": "Contatado", "order": 2, "color": "#8B5CF6", "stage_type": "open", "maps_to_status": "in process"},
    {"name": "Qualificado", "order": 3, "color": "#F59E0B", "stage_type": "open", "maps_to_status": "in process", "win_probability": 25},
    {"name": "Proposta", "order": 4, "color": "#10B981", "stage_type": "open", "maps_to_status": "in process", "win_probability": 50},
    {"name": "Ganho", "order": 5, "color": "#22C55E", "stage_type": "won", "maps_to_status": "converted", "win_probability": 100},
    {"name": "Perdido", "order": 6, "color": "#EF4444", "stage_type": "lost", "maps_to_status": "closed"},
]

OPPORTUNITY_STAGES = [
    {"name": "Prospecção", "order": 1, "color": "#3B82F6", "stage_type": "open", "maps_to_stage": "PROSPECTING", "win_probability": 10},
    {"name": "Qualificação", "order": 2, "color": "#8B5CF6", "stage_type": "open", "maps_to_stage": "QUALIFICATION", "win_probability": 25},
    {"name": "Proposta", "order": 3, "color": "#F59E0B", "stage_type": "open", "maps_to_stage": "PROPOSAL", "win_probability": 50},
    {"name": "Negociação", "order": 4, "color": "#10B981", "stage_type": "open", "maps_to_stage": "NEGOTIATION", "win_probability": 75},
    {"name": "Ganho", "order": 5, "color": "#22C55E", "stage_type": "won", "maps_to_stage": "CLOSED_WON", "win_probability": 100},
    {"name": "Perdido", "order": 6, "color": "#EF4444", "stage_type": "lost", "maps_to_stage": "CLOSED_LOST", "win_probability": 0},
]

CASE_STAGES = [
    {"name": "Novo", "order": 1, "color": "#3B82F6", "stage_type": "open", "maps_to_status": "New"},
    {"name": "Atribuído", "order": 2, "color": "#8B5CF6", "stage_type": "open", "maps_to_status": "Assigned"},
    {"name": "Em Andamento", "order": 3, "color": "#F59E0B", "stage_type": "open", "maps_to_status": "Pending"},
    {"name": "Resolvido", "order": 4, "color": "#22C55E", "stage_type": "closed", "maps_to_status": "Closed"},
    {"name": "Rejeitado", "order": 5, "color": "#EF4444", "stage_type": "rejected", "maps_to_status": "Rejected"},
]

TASK_STAGES = [
    {"name": "A Fazer", "order": 1, "color": "#3B82F6", "stage_type": "open", "maps_to_status": "New"},
    {"name": "Em Andamento", "order": 2, "color": "#F59E0B", "stage_type": "in_progress", "maps_to_status": "In Progress"},
    {"name": "Revisão", "order": 3, "color": "#8B5CF6", "stage_type": "in_progress", "maps_to_status": "In Progress"},
    {"name": "Concluído", "order": 4, "color": "#22C55E", "stage_type": "completed", "maps_to_status": "Completed"},
]


def seed_pipelines_for_org(org, stdout=None):
    """Seed default pipelines for a single org. Idempotent — skips if pipelines already exist."""
    from cases.models import CasePipeline, CaseStage
    from leads.models import LeadPipeline, LeadStage
    from opportunity.models import OpportunityPipeline, OpportunityStage
    from tasks.models import TaskPipeline, TaskStage

    # Set RLS context
    with connection.cursor() as cursor:
        cursor.execute(get_set_context_sql(), [str(org.id)])

    created_count = 0

    modules = [
        (LeadPipeline, LeadStage, LEAD_STAGES, "Leads"),
        (OpportunityPipeline, OpportunityStage, OPPORTUNITY_STAGES, "Negócios"),
        (CasePipeline, CaseStage, CASE_STAGES, "Casos"),
        (TaskPipeline, TaskStage, TASK_STAGES, "Tarefas"),
    ]

    for PipelineModel, StageModel, stages_def, label in modules:
        # Skip if org already has an active pipeline for this module
        if PipelineModel.objects.filter(org=org, is_active=True).exists():
            if stdout:
                stdout.write(f"  {label}: já possui pipeline — pulando")
            continue

        pipeline = PipelineModel.objects.create(
            name="Pipeline Padrão",
            org=org,
            is_default=True,
            is_active=True,
        )

        for stage_data in stages_def:
            StageModel.objects.create(pipeline=pipeline, org=org, **stage_data)

        created_count += 1
        if stdout:
            stdout.write(f"  {label}: pipeline criado com {len(stages_def)} estágios")

    return created_count


class Command(BaseCommand):
    help = "Seed default kanban pipelines (pt-BR) for all 4 modules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-id",
            type=str,
            help="UUID of specific organization to seed",
        )
        parser.add_argument(
            "--all-orgs",
            action="store_true",
            help="Seed all active organizations",
        )

    def handle(self, *args, **options):
        org_id = options.get("org_id")
        all_orgs = options.get("all_orgs")

        if not org_id and not all_orgs:
            raise CommandError("Specify --org-id UUID or --all-orgs")

        if org_id:
            try:
                orgs = [Org.objects.get(id=org_id)]
            except Org.DoesNotExist:
                raise CommandError(f"Organization {org_id} not found")
        else:
            orgs = list(Org.objects.filter(is_active=True))

        self.stdout.write(f"Seeding pipeline defaults for {len(orgs)} organization(s)...")

        total = 0
        for org in orgs:
            self.stdout.write(f"\nOrg: {org.name}")
            total += seed_pipelines_for_org(org, stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS(f"\nDone! Created {total} pipelines"))
