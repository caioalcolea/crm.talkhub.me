from rest_framework import serializers

from common.serializers import (
    AttachmentsSerializer,
    OrganizationSerializer,
    ProfileSerializer,
    TeamsSerializer,
)
from contacts.models import Contact, ContactAddress, ContactEmail, ContactPhone


# Note: Removed unused serializer properties that were computed but never used by frontend:
# - get_team_users, get_team_and_assigned_users, get_assigned_users_not_in_teams
# - created_on_arrow (frontend computes its own humanized timestamps)


class ContactEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactEmail
        fields = ("id", "email", "label")


class ContactPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPhone
        fields = ("id", "phone", "label")


class ContactAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactAddress
        fields = ("id", "label", "address_line", "city", "state", "postcode", "country")


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for reading Contact data"""

    teams = TeamsSerializer(read_only=True, many=True)
    assigned_to = ProfileSerializer(read_only=True, many=True)
    contact_attachment = AttachmentsSerializer(read_only=True, many=True)
    org = OrganizationSerializer()
    extra_emails = ContactEmailSerializer(many=True, read_only=True)
    extra_phones = ContactPhoneSerializer(many=True, read_only=True)
    extra_addresses = ContactAddressSerializer(many=True, read_only=True)

    class Meta:
        model = Contact
        fields = (
            "id",
            # Core Contact Information
            "first_name",
            "last_name",
            "email",
            "phone",
            "secondary_email",
            "secondary_phone",
            # Professional Information
            "organization",
            "title",
            "department",
            # Communication Preferences
            "do_not_call",
            "linkedin_url",
            # Social Media
            "instagram",
            "facebook",
            "tiktok",
            "telegram",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Assignment
            "assigned_to",
            "teams",
            # Tags
            "tags",
            # Notes
            "description",
            # System
            "created_by",
            "created_at",
            "is_active",
            "org",
            "account",
            "contact_attachment",
            # Extra contact info
            "extra_emails",
            "extra_phones",
            "extra_addresses",
        )


class CreateContactSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Contact data"""

    def __init__(self, *args, **kwargs):
        request_obj = kwargs.pop("request_obj", None)
        super().__init__(*args, **kwargs)
        if request_obj:
            self.org = request_obj.profile.org

    def validate_email(self, email):
        if email:
            if self.instance:
                if (
                    Contact.objects.filter(email__iexact=email, org=self.org)
                    .exclude(id=self.instance.id)
                    .exists()
                ):
                    raise serializers.ValidationError(
                        "Contact already exists with this email"
                    )
            else:
                if Contact.objects.filter(email__iexact=email, org=self.org).exists():
                    raise serializers.ValidationError(
                        "Contact already exists with this email"
                    )
        return email

    class Meta:
        model = Contact
        fields = (
            # Core Contact Information
            "first_name",
            "last_name",
            "email",
            "phone",
            "secondary_email",
            "secondary_phone",
            # Professional Information
            "organization",
            "title",
            "department",
            # Communication Preferences
            "do_not_call",
            "linkedin_url",
            # Social Media
            "instagram",
            "facebook",
            "tiktok",
            "telegram",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Notes
            "description",
            # Account
            "account",
            # Status
            "is_active",
        )


class ContactDetailEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()
    contact_attachment = serializers.FileField()


class ContactCommentEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()


class MergeRequestSerializer(serializers.Serializer):
    primary_id = serializers.UUIDField()
    secondary_id = serializers.UUIDField()

    def validate(self, data):
        if data["primary_id"] == data["secondary_id"]:
            raise serializers.ValidationError(
                "Os contatos principal e secundário devem ser diferentes."
            )
        return data


class DuplicateContactSerializer(serializers.ModelSerializer):
    match_reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)
    channels = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Contact
        fields = (
            "id", "first_name", "last_name", "email", "phone",
            "secondary_email", "secondary_phone",
            "organization", "source",
            "match_reasons", "conversations_count", "channels",
        )
