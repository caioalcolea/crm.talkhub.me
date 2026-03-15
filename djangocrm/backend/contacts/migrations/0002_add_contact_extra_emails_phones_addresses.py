# Generated manually for extra contact emails, phones, and addresses

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContactEmail",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("email", models.EmailField(max_length=254, verbose_name="Email")),
                (
                    "label",
                    models.CharField(
                        choices=[
                            ("work", "Trabalho"),
                            ("personal", "Pessoal"),
                            ("other", "Outro"),
                        ],
                        default="work",
                        max_length=20,
                        verbose_name="Label",
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_emails",
                        to="contacts.contact",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Contact Email",
                "verbose_name_plural": "Contact Emails",
                "db_table": "contact_emails",
                "ordering": ("label", "email"),
            },
        ),
        migrations.CreateModel(
            name="ContactPhone",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        max_length=25,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Enter a valid phone number (7-25 characters, digits and separators only)",
                                regex="^[\\d\\s\\-\\(\\)\\+\\.]{7,25}$",
                            )
                        ],
                        verbose_name="Phone",
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        choices=[
                            ("work", "Trabalho"),
                            ("personal", "Pessoal"),
                            ("mobile", "Celular"),
                            ("whatsapp", "WhatsApp"),
                            ("other", "Outro"),
                        ],
                        default="mobile",
                        max_length=20,
                        verbose_name="Label",
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_phones",
                        to="contacts.contact",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Contact Phone",
                "verbose_name_plural": "Contact Phones",
                "db_table": "contact_phones",
                "ordering": ("label", "phone"),
            },
        ),
        migrations.CreateModel(
            name="ContactAddress",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        choices=[
                            ("work", "Trabalho"),
                            ("home", "Residência"),
                            ("billing", "Cobrança"),
                            ("shipping", "Entrega"),
                            ("other", "Outro"),
                        ],
                        default="work",
                        max_length=20,
                        verbose_name="Label",
                    ),
                ),
                (
                    "address_line",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Address"
                    ),
                ),
                (
                    "city",
                    models.CharField(blank=True, max_length=255, verbose_name="City"),
                ),
                (
                    "state",
                    models.CharField(blank=True, max_length=255, verbose_name="State"),
                ),
                (
                    "postcode",
                    models.CharField(
                        blank=True, max_length=64, verbose_name="Postal Code"
                    ),
                ),
                (
                    "country",
                    models.CharField(
                        blank=True, max_length=3, verbose_name="Country"
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_addresses",
                        to="contacts.contact",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Contact Address",
                "verbose_name_plural": "Contact Addresses",
                "db_table": "contact_addresses",
                "ordering": ("label",),
            },
        ),
    ]
