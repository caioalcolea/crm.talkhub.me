from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from common.base import AssignableMixin, BaseModel, OrgScopedMixin
from common.models import Org, Profile, Tags, Teams
from common.utils import CONTACT_SOURCE, COUNTRIES
from common.validators import flexible_phone_validator


class Contact(AssignableMixin, OrgScopedMixin, BaseModel):
    """
    Contact model for CRM - Streamlined for modern sales workflow
    Based on Twenty CRM and Salesforce patterns
    """

    # Core Contact Information
    first_name = models.CharField(_("First name"), max_length=255)
    last_name = models.CharField(_("Last name"), max_length=255)
    email = models.EmailField(_("Email"), blank=True, null=True)
    phone = models.CharField(
        _("Phone"),
        max_length=25,
        null=True,
        blank=True,
        validators=[flexible_phone_validator],
    )
    secondary_email = models.EmailField(_("Secondary Email"), blank=True, null=True)
    secondary_phone = models.CharField(
        _("Secondary Phone"),
        max_length=25,
        null=True,
        blank=True,
        validators=[flexible_phone_validator],
    )

    # Professional Information
    organization = models.CharField(_("Company"), max_length=255, blank=True, null=True)
    title = models.CharField(_("Job Title"), max_length=255, blank=True, null=True)
    department = models.CharField(
        _("Department"), max_length=255, blank=True, null=True
    )

    # Communication Preferences
    do_not_call = models.BooleanField(_("Do Not Call"), default=False)
    linkedin_url = models.URLField(_("LinkedIn URL"), blank=True, null=True)

    # Social Media (used for omni inbox channel integration)
    instagram = models.CharField(_("Instagram"), max_length=255, blank=True, null=True)
    facebook = models.CharField(_("Facebook"), max_length=255, blank=True, null=True)
    tiktok = models.CharField(_("TikTok"), max_length=255, blank=True, null=True)
    telegram = models.CharField(_("Telegram"), max_length=255, blank=True, null=True)

    # Address (flat fields like Lead model)
    address_line = models.CharField(_("Address"), max_length=255, blank=True, null=True)
    city = models.CharField(_("City"), max_length=255, blank=True, null=True)
    state = models.CharField(_("State"), max_length=255, blank=True, null=True)
    postcode = models.CharField(_("Postal Code"), max_length=64, blank=True, null=True)
    country = models.CharField(
        _("Country"), max_length=3, choices=COUNTRIES, blank=True, null=True
    )

    # Assignment
    assigned_to = models.ManyToManyField(Profile, related_name="contact_assigned_users")
    teams = models.ManyToManyField(Teams, related_name="contact_teams")

    # Tags
    tags = models.ManyToManyField(Tags, related_name="contact_tags", blank=True)

    # Notes
    description = models.TextField(_("Notes"), blank=True, null=True)

    # System Fields
    is_active = models.BooleanField(default=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="contacts")

    # Account relationship (optional - contact can exist without an account)
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_contacts",
        help_text="Primary account this contact belongs to",
    )

    # Source / Channel tracking
    source = models.CharField(
        _("Source"), max_length=100, blank=True, null=True,
        choices=CONTACT_SOURCE,
        help_text="Canal de origem do contato",
    )
    talkhub_channel_type = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Tipo do canal TalkHub (whatsapp, facebook, instagram, etc.)",
    )
    talkhub_channel_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="ID do canal TalkHub de origem",
    )

    # TalkHub Omni integration
    talkhub_subscriber_id = models.CharField(
        max_length=100, blank=True, null=True, db_index=True,
        help_text="TalkHub Omni subscriber user_ns",
    )

    # Omni correlation fields
    sms_opt_in = models.BooleanField(_("SMS Opt-In"), default=True)
    email_opt_in = models.BooleanField(_("Email Opt-In"), default=True)
    omni_user_ns = models.CharField(
        _("Omni User NS"),
        max_length=100, blank=True, null=True, db_index=True,
        help_text="Alias de talkhub_subscriber_id para correlação Omni",
    )

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        db_table = "contacts"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["org", "-created_at"]),
            models.Index(fields=["org", "source"]),
        ]
        constraints = [
            # Case-insensitive unique email per organization (when email is not null)
            models.UniqueConstraint(
                Lower("email"),
                "org",
                name="unique_contact_email_per_org",
                condition=Q(email__isnull=False) & ~Q(email=""),
            ),
        ]

    def __str__(self):
        return self.first_name


class ContactEmail(BaseModel):
    """Additional email addresses for a contact (beyond the primary email)."""

    LABEL_CHOICES = [
        ("work", "Trabalho"),
        ("personal", "Pessoal"),
        ("other", "Outro"),
    ]

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="extra_emails"
    )
    email = models.EmailField(_("Email"))
    label = models.CharField(
        _("Label"), max_length=20, choices=LABEL_CHOICES, default="work"
    )

    class Meta:
        verbose_name = "Contact Email"
        verbose_name_plural = "Contact Emails"
        db_table = "contact_emails"
        ordering = ("label", "email")

    def __str__(self):
        return f"{self.email} ({self.label})"


class ContactPhone(BaseModel):
    """Additional phone numbers for a contact (beyond the primary phone)."""

    LABEL_CHOICES = [
        ("work", "Trabalho"),
        ("personal", "Pessoal"),
        ("mobile", "Celular"),
        ("whatsapp", "WhatsApp"),
        ("other", "Outro"),
    ]

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="extra_phones"
    )
    phone = models.CharField(
        _("Phone"), max_length=25, validators=[flexible_phone_validator]
    )
    label = models.CharField(
        _("Label"), max_length=20, choices=LABEL_CHOICES, default="mobile"
    )

    class Meta:
        verbose_name = "Contact Phone"
        verbose_name_plural = "Contact Phones"
        db_table = "contact_phones"
        ordering = ("label", "phone")

    def __str__(self):
        return f"{self.phone} ({self.label})"


class ContactAddress(BaseModel):
    """Additional addresses for a contact (beyond the primary address)."""

    LABEL_CHOICES = [
        ("work", "Trabalho"),
        ("home", "Residência"),
        ("billing", "Cobrança"),
        ("shipping", "Entrega"),
        ("other", "Outro"),
    ]

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="extra_addresses"
    )
    label = models.CharField(
        _("Label"), max_length=20, choices=LABEL_CHOICES, default="work"
    )
    address_line = models.CharField(_("Address"), max_length=255, blank=True)
    city = models.CharField(_("City"), max_length=255, blank=True)
    state = models.CharField(_("State"), max_length=255, blank=True)
    postcode = models.CharField(_("Postal Code"), max_length=64, blank=True)
    country = models.CharField(
        _("Country"), max_length=3, choices=COUNTRIES, blank=True
    )

    class Meta:
        verbose_name = "Contact Address"
        verbose_name_plural = "Contact Addresses"
        db_table = "contact_addresses"
        ordering = ("label",)

    def __str__(self):
        parts = [self.address_line, self.city, self.state]
        return ", ".join(p for p in parts if p) or f"Endereço ({self.label})"
