"""
Add Notification and JobAttempt models for Phase 2 — robust motor.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0004_enable_rls_session"),
        ("common", "0001_initial"),
    ]

    operations = [
        # ── Notification ──────────────────────────────────────────
        migrations.CreateModel(
            name="Notification",
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
                    "type",
                    models.CharField(
                        choices=[
                            ("job_completed", "Job concluído"),
                            ("job_failed", "Job falhou"),
                            ("approval_pending", "Aprovação pendente"),
                            ("campaign_done", "Campanha concluída"),
                            ("system", "Sistema"),
                        ],
                        max_length=30,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField(blank=True, default="")),
                ("link", models.CharField(blank=True, default="", max_length=500)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to="common.profile",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to="common.profile",
                        verbose_name="Updated By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="common.profile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notification",
                "verbose_name_plural": "Notifications",
                "db_table": "notification",
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["org", "user", "-created_at"],
                name="notificatio_org_id_crt_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["org", "user", "read_at"],
                name="idx_notification_unread",
            ),
        ),
        # ── JobAttempt ────────────────────────────────────────────
        migrations.CreateModel(
            name="JobAttempt",
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
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("attempt_number", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Em execução"),
                            ("success", "Sucesso"),
                            ("failed", "Falhou"),
                            ("rate_limited", "Rate limited"),
                            ("deferred", "Adiado"),
                        ],
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField()),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("channel_type", models.CharField(blank=True, default="", max_length=50)),
                ("destination", models.CharField(blank=True, default="", max_length=255)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to="common.profile",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="assistant.scheduledjob",
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to="common.profile",
                        verbose_name="Updated By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Job Attempt",
                "verbose_name_plural": "Job Attempts",
                "db_table": "assistant_job_attempt",
            },
        ),
        migrations.AddIndex(
            model_name="jobattempt",
            index=models.Index(
                fields=["job", "attempt_number"],
                name="assistant_j_job_att_idx",
            ),
        ),
    ]
