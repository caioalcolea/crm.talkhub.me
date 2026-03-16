# Add order_type field to Order model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_type",
            field=models.CharField(
                choices=[("sales", "Pedido de Venda"), ("purchase", "Pedido de Compra")],
                default="sales",
                max_length=10,
                verbose_name="Order Type",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["org", "order_type", "-created_at"],
                name="orders_org_type_created_idx",
            ),
        ),
    ]
