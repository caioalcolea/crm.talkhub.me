"""
Models do app automations.

- Automation: Automação configurável por org (routine, logic_rule, social).
- AutomationLog: Log de execução de automação.
"""

from django.db import models

from common.base import BaseOrgModel


class Automation(BaseOrgModel):
    """Automação configurável por organização."""

    TYPE_CHOICES = [
        ("routine", "Routine"),
        ("logic_rule", "Logic Rule"),
        ("social", "Social"),
    ]

    name = models.CharField(max_length=255)
    automation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=False)
    config_json = models.JSONField(default=dict, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "automation"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["automation_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.automation_type}) - {self.org}"


class AutomationLog(BaseOrgModel):
    """Log de execução de automação."""

    STATUS_CHOICES = [
        ("success", "Success"),
        ("error", "Error"),
        ("skipped", "Skipped"),
    ]

    automation = models.ForeignKey(
        Automation,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    trigger_data = models.JSONField(default=dict, blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    error_detail = models.TextField(blank=True, default="")
    execution_time_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "automation_log"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["automation", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Log {self.status} - {self.automation.name}"
