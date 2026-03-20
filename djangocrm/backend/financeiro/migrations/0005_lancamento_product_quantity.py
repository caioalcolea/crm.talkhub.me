import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0004_centro_custos_enhancements"),
        ("invoices", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lancamento",
            name="product",
            field=models.ForeignKey(
                blank=True,
                help_text="Produto/serviço associado (opcional)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lancamentos",
                to="invoices.product",
            ),
        ),
        migrations.AddField(
            model_name="lancamento",
            name="quantity",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1"),
                help_text="Quantidade do produto/serviço",
                max_digits=12,
            ),
        ),
    ]
