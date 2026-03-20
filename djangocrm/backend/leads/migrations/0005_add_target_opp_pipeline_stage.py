import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0004_translate_stage_names"),
        ("opportunity", "0002_opportunity_pipeline"),
    ]

    operations = [
        migrations.AddField(
            model_name="leadpipeline",
            name="target_opp_pipeline",
            field=models.ForeignKey(
                blank=True,
                help_text="Pipeline de oportunidade onde o negócio será criado",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="opportunity.opportunitypipeline",
            ),
        ),
        migrations.AddField(
            model_name="leadpipeline",
            name="target_opp_stage",
            field=models.ForeignKey(
                blank=True,
                help_text="Etapa inicial da oportunidade criada (padrão: 1ª etapa do pipeline)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="opportunity.opportunitystage",
            ),
        ),
    ]
