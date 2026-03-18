from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0003_translate_stage_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="due_time",
            field=models.TimeField(blank=True, null=True, verbose_name="due time"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(
                fields=["due_date", "due_time"],
                name="task_due_dat_due_tim_idx",
            ),
        ),
    ]
