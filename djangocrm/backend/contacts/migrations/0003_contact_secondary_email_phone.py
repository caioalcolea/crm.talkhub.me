"""Add secondary_email and secondary_phone fields to Contact model."""

from django.db import migrations, models
import common.validators


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0002_add_contact_extra_emails_phones_addresses"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="secondary_email",
            field=models.EmailField(
                blank=True, max_length=254, null=True, verbose_name="Secondary Email"
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="secondary_phone",
            field=models.CharField(
                blank=True,
                max_length=25,
                null=True,
                validators=[common.validators.flexible_phone_validator],
                verbose_name="Secondary Phone",
            ),
        ),
    ]
