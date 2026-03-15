"""
Add exchange_rate_type, recurring lancamento fields.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lancamento",
            name="exchange_rate_type",
            field=models.CharField(
                choices=[("FIXO", "Fixo"), ("VARIAVEL", "Variável")],
                default="FIXO",
                help_text="FIXO = manual, VARIAVEL = busca automática da API",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="lancamento",
            name="is_recorrente",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="lancamento",
            name="recorrencia_tipo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MENSAL", "Mensal"),
                    ("QUINZENAL", "Quinzenal"),
                    ("SEMANAL", "Semanal"),
                    ("ANUAL", "Anual"),
                ],
                max_length=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="lancamento",
            name="data_fim_recorrencia",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="lancamento",
            name="recorrencia_ativa",
            field=models.BooleanField(default=True),
        ),
    ]
