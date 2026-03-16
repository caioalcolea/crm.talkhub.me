# Product evolution: add type, cost, taxes, fees, inventory fields + StockMovement model

import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_initial"),
        ("common", "0001_initial"),
        ("financeiro", "0001_initial"),
        ("invoices", "0002_initial"),
    ]

    operations = [
        # =====================================================================
        # Product: New fields for type, cost, taxes, fees, inventory
        # =====================================================================
        migrations.AddField(
            model_name="product",
            name="product_type",
            field=models.CharField(
                choices=[("product", "Produto"), ("service", "Serviço")],
                default="product",
                max_length=20,
                verbose_name="Type",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="cost_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Purchase/production cost for margin calculation",
                max_digits=12,
                verbose_name="Cost Price",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="default_tax_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Default tax rate applied when adding to invoices",
                max_digits=5,
                verbose_name="Default Tax Rate (%)",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="tax_profile",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='{"icms": 18, "iss": 5, "pis": 1.65, "cofins": 7.6}',
                verbose_name="Tax Profile",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="gateway_fee_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Payment gateway/marketplace fee percentage (e.g., 3.5% Moip)",
                max_digits=5,
                verbose_name="Gateway Fee (%)",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="gateway_fee_fixed",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Fixed fee per transaction (e.g., R$0.50)",
                max_digits=8,
                verbose_name="Gateway Fee (Fixed)",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="track_inventory",
            field=models.BooleanField(default=False, verbose_name="Track Inventory"),
        ),
        migrations.AddField(
            model_name="product",
            name="stock_quantity",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name="Stock Quantity",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="stock_min_alert",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Alert when stock falls below this quantity",
                max_digits=12,
                verbose_name="Min Stock Alert",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="unit_of_measure",
            field=models.CharField(
                blank=True,
                default="un",
                help_text="un, kg, hr, mês, licença",
                max_length=20,
                verbose_name="Unit of Measure",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="supplier_account",
            field=models.ForeignKey(
                blank=True,
                help_text="Preferred supplier for purchase orders",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supplied_products",
                to="accounts.account",
                verbose_name="Supplier",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="default_plano_receita",
            field=models.ForeignKey(
                blank=True,
                help_text="Default revenue account for financeiro integration",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="financeiro.planodecontas",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="default_plano_custo",
            field=models.ForeignKey(
                blank=True,
                help_text="Default cost account for COGS entries",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="financeiro.planodecontas",
            ),
        ),
        # New index for product_type
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["org", "product_type"],
                name="product_org_type_idx",
            ),
        ),
        # =====================================================================
        # StockMovement model
        # =====================================================================
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="common.profile",
                    ),
                ),
                (
                    "movement_type",
                    models.CharField(
                        choices=[
                            ("in", "Entrada"),
                            ("out", "Saída"),
                            ("adjustment", "Ajuste"),
                        ],
                        max_length=10,
                        verbose_name="Movement Type",
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="Quantity"
                    ),
                ),
                (
                    "unit_cost",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Unit Cost",
                    ),
                ),
                (
                    "reference_type",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="invoice, order, purchase, manual",
                        max_length=30,
                        verbose_name="Reference Type",
                    ),
                ),
                (
                    "reference_id",
                    models.UUIDField(
                        blank=True,
                        help_text="UUID of the related document",
                        null=True,
                        verbose_name="Reference ID",
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, default="", verbose_name="Notes"),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_movements",
                        to="invoices.product",
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_movements",
                        to="common.org",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Movement",
                "verbose_name_plural": "Stock Movements",
                "db_table": "stock_movement",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["org", "-created_at"],
                name="stock_mov_org_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["product", "-created_at"],
                name="stock_mov_product_created_idx",
            ),
        ),
    ]
