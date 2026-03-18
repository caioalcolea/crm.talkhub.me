"""Add Subtask, TaskDependency, Project models + effort/impact/project fields on Task."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0004_add_due_time"),
        ("cases", "0004_translate_stage_names"),
        ("common", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Project model ---
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("color", models.CharField(default="#6366F1", max_length=7)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Ativo"),
                            ("completed", "Concluído"),
                            ("archived", "Arquivado"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("due_date", models.DateField(blank=True, null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_projects",
                        to="common.profile",
                    ),
                ),
                (
                    "members",
                    models.ManyToManyField(
                        blank=True, related_name="projects", to="common.profile"
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="projects",
                        to="common.org",
                    ),
                ),
            ],
            options={
                "verbose_name": "Project",
                "verbose_name_plural": "Projects",
                "db_table": "project",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(fields=["org", "-created_at"], name="project_org_created_idx"),
                    models.Index(fields=["status"], name="project_status_idx"),
                ],
            },
        ),
        # --- Task: effort, impact, project fields ---
        migrations.AddField(
            model_name="task",
            name="effort",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, "Baixo"), (2, "Médio"), (3, "Alto")],
                null=True,
                verbose_name="effort",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="impact",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, "Baixo"), (2, "Médio"), (3, "Alto")],
                null=True,
                verbose_name="impact",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="tasks.project",
            ),
        ),
        # --- Subtask model ---
        migrations.CreateModel(
            name="Subtask",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=300)),
                ("is_completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_subtasks",
                        to="common.profile",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subtasks",
                        to="tasks.task",
                    ),
                ),
                (
                    "case",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subtasks",
                        to="cases.case",
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subtasks",
                        to="common.org",
                    ),
                ),
            ],
            options={
                "verbose_name": "Subtask",
                "verbose_name_plural": "Subtasks",
                "db_table": "subtask",
                "ordering": ["order", "created_at"],
                "indexes": [
                    models.Index(fields=["task", "order"], name="subtask_task_order_idx"),
                    models.Index(fields=["case", "order"], name="subtask_case_order_idx"),
                    models.Index(fields=["org"], name="subtask_org_idx"),
                ],
            },
        ),
        # --- TaskDependency model ---
        migrations.CreateModel(
            name="TaskDependency",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependencies",
                        to="tasks.task",
                    ),
                ),
                (
                    "depends_on",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependents",
                        to="tasks.task",
                    ),
                ),
                (
                    "dependency_type",
                    models.CharField(
                        choices=[("blocks", "Bloqueia"), ("related", "Relacionada")],
                        default="blocks",
                        max_length=20,
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_dependencies",
                        to="common.org",
                    ),
                ),
            ],
            options={
                "verbose_name": "Task Dependency",
                "verbose_name_plural": "Task Dependencies",
                "db_table": "task_dependency",
                "unique_together": {("task", "depends_on")},
                "indexes": [
                    models.Index(fields=["task"], name="taskdep_task_idx"),
                    models.Index(fields=["depends_on"], name="taskdep_depson_idx"),
                    models.Index(fields=["org"], name="taskdep_org_idx"),
                ],
            },
        ),
    ]
