"""
Add Centro de Custos enhancements:
- PlanoDeContasGrupo: color, applies_to, is_system_default
- PlanoDeContas: code, is_system_default, sort_order
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0003_lancamento_financeiro_improvements"),
    ]

    operations = [
        # PlanoDeContasGrupo new fields
        migrations.AddField(
            model_name="planodecontasgrupo",
            name="color",
            field=models.CharField(
                max_length=7,
                default="#6B7280",
                help_text="Cor hex para exibição no frontend",
            ),
        ),
        migrations.AddField(
            model_name="planodecontasgrupo",
            name="applies_to",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("AMBOS", "Ambos"),
                    ("PAGAR", "Pagar"),
                    ("RECEBER", "Receber"),
                ],
                default="AMBOS",
                help_text="Tipo de lançamento ao qual este grupo se aplica",
            ),
        ),
        migrations.AddField(
            model_name="planodecontasgrupo",
            name="is_system_default",
            field=models.BooleanField(
                default=False,
                help_text="Grupos padrão do sistema não podem ser deletados",
            ),
        ),
        # PlanoDeContas new fields
        migrations.AddField(
            model_name="planodecontas",
            name="code",
            field=models.CharField(
                max_length=20,
                blank=True,
                default="",
                help_text="Código interno opcional",
            ),
        ),
        migrations.AddField(
            model_name="planodecontas",
            name="is_system_default",
            field=models.BooleanField(
                default=False,
                help_text="Contas padrão do sistema não podem ser deletadas",
            ),
        ),
        migrations.AddField(
            model_name="planodecontas",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Ordem de exibição dentro do grupo",
            ),
        ),
    ]
