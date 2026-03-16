"""
Add OpportunityPipeline and OpportunityStage models,
plus pipeline_stage FK and kanban_order on Opportunity.
"""

import django.db.models.deletion
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunity", "0001_initial"),
        ("common", "0001_initial"),
    ]

    operations = [
        # --- OpportunityPipeline ---
        migrations.CreateModel(
            name="OpportunityPipeline",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, verbose_name="Pipeline Name"),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, null=True, verbose_name="Description"
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="opportunity_pipelines",
                        to="common.org",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="If true, new opportunities without explicit pipeline go here",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "visible_to_teams",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Se vazio = visível para todos. Se preenchido = apenas estes times.",
                        related_name="visible_opportunity_pipelines",
                        to="common.teams",
                    ),
                ),
                (
                    "visible_to_users",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Se vazio = visível para todos. Se preenchido = apenas estes usuários.",
                        related_name="visible_opportunity_pipelines",
                        to="common.profile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Opportunity Pipeline",
                "verbose_name_plural": "Opportunity Pipelines",
                "db_table": "opportunity_pipeline",
                "ordering": ("-is_default", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="opportunitypipeline",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True)),
                fields=("org",),
                name="unique_default_opportunity_pipeline_per_org",
            ),
        ),
        migrations.AddIndex(
            model_name="opportunitypipeline",
            index=models.Index(
                fields=["org", "-created_at"],
                name="opp_pipeline_org_created_idx",
            ),
        ),
        # --- OpportunityStage ---
        migrations.CreateModel(
            name="OpportunityStage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pipeline",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stages",
                        to="opportunity.opportunitypipeline",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100, verbose_name="Stage Name"),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                ("color", models.CharField(default="#6B7280", max_length=7)),
                (
                    "stage_type",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("won", "Won"),
                            ("lost", "Lost"),
                        ],
                        default="open",
                        max_length=10,
                    ),
                ),
                (
                    "maps_to_stage",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PROSPECTING", "Prospecting"),
                            ("QUALIFICATION", "Qualification"),
                            ("PROPOSAL", "Proposal"),
                            ("NEGOTIATION", "Negotiation"),
                            ("CLOSED_WON", "Closed Won"),
                            ("CLOSED_LOST", "Closed Lost"),
                        ],
                        help_text="When opportunity enters this stage, also update the legacy stage CharField",
                        max_length=64,
                        null=True,
                        verbose_name="Maps to Legacy Stage",
                    ),
                ),
                (
                    "win_probability",
                    models.IntegerField(
                        default=0,
                        help_text="Default probability when opportunity enters this stage",
                        verbose_name="Default Win Probability %",
                    ),
                ),
                (
                    "wip_limit",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum opportunities allowed in this stage (null = unlimited)",
                        null=True,
                        verbose_name="WIP Limit",
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="opportunity_stages",
                        to="common.org",
                    ),
                ),
            ],
            options={
                "verbose_name": "Opportunity Stage",
                "verbose_name_plural": "Opportunity Stages",
                "db_table": "opportunity_stage",
                "ordering": ("order",),
                "unique_together": {("pipeline", "name")},
            },
        ),
        migrations.AddIndex(
            model_name="opportunitystage",
            index=models.Index(
                fields=["org", "order"],
                name="opp_stage_org_order_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="opportunitystage",
            index=models.Index(
                fields=["pipeline", "order"],
                name="opp_stage_pipeline_order_idx",
            ),
        ),
        # --- Add fields to Opportunity ---
        migrations.AddField(
            model_name="opportunity",
            name="pipeline_stage",
            field=models.ForeignKey(
                blank=True,
                help_text="Pipeline stage (null = use legacy stage CharField)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="opportunities",
                to="opportunity.opportunitystage",
            ),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="kanban_order",
            field=models.DecimalField(
                decimal_places=6,
                default=0,
                help_text="Order within the kanban column for drag-drop positioning",
                max_digits=15,
                verbose_name="Kanban Order",
            ),
        ),
        migrations.AddIndex(
            model_name="opportunity",
            index=models.Index(
                fields=["pipeline_stage", "kanban_order"],
                name="opp_pipeline_stage_order_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="opportunity",
            index=models.Index(
                fields=["stage", "kanban_order"],
                name="opp_stage_kanban_order_idx",
            ),
        ),
    ]
