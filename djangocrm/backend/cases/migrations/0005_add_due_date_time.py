"""Add due_date and due_time fields to Case model."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0004_translate_stage_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="case",
            name="due_date",
            field=models.DateField(
                blank=True, null=True, verbose_name="due date"
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="due_time",
            field=models.TimeField(
                blank=True, null=True, verbose_name="due time"
            ),
        ),
        migrations.AddIndex(
            model_name="case",
            index=models.Index(
                fields=["due_date"], name="case_due_date_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="case",
            index=models.Index(
                fields=["due_date", "due_time"], name="case_due_datetime_idx"
            ),
        ),
    ]
