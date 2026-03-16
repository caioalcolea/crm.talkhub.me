"""
Add AssistantSession and AssistantMessage models for conversational AI assistant.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0002_enable_rls"),
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssistantSession",
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
                ("title", models.CharField(blank=True, default="", max_length=200)),
                ("context_json", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Ativa"), ("archived", "Arquivada")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("last_activity_at", models.DateTimeField(auto_now=True)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                (
                    "total_cost_usd",
                    models.DecimalField(decimal_places=6, default=0, max_digits=10),
                ),
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
                        related_name="assistant_sessions",
                        to="common.profile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assistant Session",
                "verbose_name_plural": "Assistant Sessions",
                "db_table": "assistant_session",
            },
        ),
        migrations.AddIndex(
            model_name="assistantsession",
            index=models.Index(
                fields=["org", "user", "-last_activity_at"],
                name="assistant_s_org_id_7e8f3a_idx",
            ),
        ),
        migrations.CreateModel(
            name="AssistantMessage",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("user", "Usuário"),
                            ("assistant", "Assistente"),
                            ("system", "Sistema"),
                            ("tool_call", "Chamada de ferramenta"),
                            ("tool_result", "Resultado de ferramenta"),
                        ],
                        max_length=20,
                    ),
                ),
                ("content", models.TextField()),
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
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="assistant.assistantsession",
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
                "verbose_name": "Assistant Message",
                "verbose_name_plural": "Assistant Messages",
                "db_table": "assistant_message",
                "ordering": ["created_at"],
            },
        ),
    ]
