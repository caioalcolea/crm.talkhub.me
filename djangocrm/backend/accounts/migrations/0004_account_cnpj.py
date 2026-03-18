from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_fix_recieved_email_typo"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="cnpj",
            field=models.CharField(
                blank=True,
                help_text="CNPJ da empresa (apenas dígitos ou formatado)",
                max_length=18,
                null=True,
                verbose_name="CNPJ",
            ),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                condition=models.Q(cnpj__isnull=False) & ~models.Q(cnpj=""),
                fields=["cnpj", "org"],
                name="unique_cnpj_per_org",
            ),
        ),
    ]
