import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("common", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReminderPolicy",
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
                        to="common.profile",
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
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "target_content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reminder_policies",
                        to="contenttypes.contenttype",
                    ),
                ),
                ("target_object_id", models.UUIDField()),
                (
                    "module_key",
                    models.CharField(
                        choices=[
                            ("financeiro", "Financeiro"),
                            ("leads", "Leads"),
                            ("cases", "Cases"),
                            ("tasks", "Tasks"),
                            ("invoices", "Invoices"),
                            ("orders", "Orders"),
                            ("opportunity", "Oportunidades"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "owner_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_reminder_policies",
                        to="common.profile",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "trigger_type",
                    models.CharField(
                        choices=[
                            ("due_date", "Data de vencimento"),
                            ("relative_date", "Relativo a data"),
                            ("recurring", "Recorrente"),
                            ("cron", "Cron expression"),
                            ("event_plus_offset", "Evento + offset"),
                        ],
                        max_length=30,
                    ),
                ),
                ("trigger_config", models.JSONField(default=dict)),
                ("channel_config", models.JSONField(default=dict)),
                ("task_config", models.JSONField(default=dict)),
                ("message_template", models.TextField(blank=True, default="")),
                (
                    "approval_policy",
                    models.CharField(
                        choices=[
                            ("auto", "Auto"),
                            ("manual", "Aprovação manual"),
                        ],
                        default="auto",
                        max_length=20,
                    ),
                ),
                (
                    "timezone",
                    models.CharField(default="America/Sao_Paulo", max_length=50),
                ),
                (
                    "next_run_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("run_count", models.PositiveIntegerField(default=0)),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Reminder Policy",
                "verbose_name_plural": "Reminder Policies",
                "db_table": "assistant_reminder_policy",
            },
        ),
        migrations.CreateModel(
            name="ScheduledJob",
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
                        to="common.profile",
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
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                (
                    "job_type",
                    models.CharField(
                        choices=[
                            ("reminder", "Lembrete"),
                            ("automation", "Automação"),
                            ("campaign_step", "Passo de campanha"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "source_content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                ("source_object_id", models.UUIDField()),
                (
                    "target_content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "target_object_id",
                    models.UUIDField(blank=True, null=True),
                ),
                (
                    "assigned_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_jobs",
                        to="common.profile",
                    ),
                ),
                ("due_at", models.DateTimeField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("locked", "Em execução"),
                            ("completed", "Concluído"),
                            ("failed", "Falhou"),
                            ("cancelled", "Cancelado"),
                            ("skipped", "Ignorado"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=3)),
                ("last_error", models.TextField(blank=True, default="")),
                ("payload", models.JSONField(default=dict)),
                (
                    "idempotency_key",
                    models.CharField(max_length=255, unique=True),
                ),
                ("approval_required", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Scheduled Job",
                "verbose_name_plural": "Scheduled Jobs",
                "db_table": "assistant_scheduled_job",
            },
        ),
        migrations.CreateModel(
            name="ChannelDispatch",
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
                        to="common.profile",
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
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                (
                    "scheduled_job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dispatches",
                        to="assistant.scheduledjob",
                    ),
                ),
                ("channel_type", models.CharField(max_length=50)),
                (
                    "provider_key",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("destination", models.CharField(max_length=255)),
                ("message_payload", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("sent", "Enviado"),
                            ("delivered", "Entregue"),
                            ("failed", "Falhou"),
                            ("bounced", "Bounce"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "provider_message_id",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Channel Dispatch",
                "verbose_name_plural": "Channel Dispatches",
                "db_table": "assistant_channel_dispatch",
            },
        ),
        migrations.CreateModel(
            name="TaskLink",
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
                        to="common.profile",
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
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                (
                    "source_content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                ("source_object_id", models.UUIDField()),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_links",
                        to="tasks.task",
                    ),
                ),
                (
                    "sync_mode",
                    models.CharField(
                        choices=[
                            ("persistent", "Persistente"),
                            ("per_run", "Por execução"),
                        ],
                        default="per_run",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Ativo"),
                            ("completed", "Concluído"),
                            ("cancelled", "Cancelado"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "Task Link",
                "verbose_name_plural": "Task Links",
                "db_table": "assistant_task_link",
            },
        ),
        migrations.CreateModel(
            name="AutopilotTemplate",
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
                        to="common.profile",
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
                    "org",
                    models.ForeignKey(
                        help_text="Organization this record belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="common.org",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("cobranca", "Cobrança"),
                            ("follow_up", "Follow-up"),
                            ("onboarding", "Onboarding"),
                            ("sla", "SLA"),
                            ("nurture", "Nutrição"),
                            ("operational", "Operacional"),
                        ],
                        max_length=50,
                    ),
                ),
                ("module_key", models.CharField(max_length=50)),
                (
                    "template_type",
                    models.CharField(
                        choices=[
                            ("reminder", "Lembrete"),
                            ("rule", "Regra"),
                            ("campaign", "Campanha"),
                        ],
                        max_length=30,
                    ),
                ),
                ("config_template", models.JSONField(default=dict)),
                ("message_template", models.TextField(blank=True, default="")),
                ("is_system", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Autopilot Template",
                "verbose_name_plural": "Autopilot Templates",
                "db_table": "assistant_autopilot_template",
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name="reminderpolicy",
            index=models.Index(
                fields=["org", "module_key", "is_active"],
                name="assistant_r_org_id_module_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reminderpolicy",
            index=models.Index(
                fields=["org", "next_run_at"],
                name="assistant_r_org_id_next_run_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reminderpolicy",
            index=models.Index(
                fields=["target_content_type", "target_object_id"],
                name="idx_reminder_policy_target",
            ),
        ),
        migrations.AddIndex(
            model_name="scheduledjob",
            index=models.Index(
                fields=["org", "status", "due_at"],
                name="assistant_s_org_id_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="tasklink",
            index=models.Index(
                fields=["source_content_type", "source_object_id"],
                name="idx_task_link_source",
            ),
        ),
        migrations.AddIndex(
            model_name="tasklink",
            index=models.Index(
                fields=["task"],
                name="assistant_t_task_id_idx",
            ),
        ),
    ]
