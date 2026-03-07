"""
Audience builder for campaigns.

Builds Contact querysets based on filter_criteria JSON.
Respects opt-in preferences per campaign type.
"""

from django.db.models import Q

from contacts.models import Contact


def build_audience_queryset(org, campaign_type, filter_criteria):
    """
    Build a Contact queryset based on filter criteria and campaign type.

    Args:
        org: Organization instance
        campaign_type: 'email_blast', 'whatsapp_broadcast', or 'nurture_sequence'
        filter_criteria: dict with filter keys

    Supported criteria:
        - tags: list of tag names
        - source: string
        - city: string
        - state: string
        - created_after: ISO date string
        - created_before: ISO date string
        - has_email: bool
        - has_phone: bool
        - is_active: bool

    Returns:
        QuerySet of Contact objects
    """
    qs = Contact.objects.filter(org=org, is_active=True)

    # Opt-in filtering by campaign type
    if campaign_type == "email_blast":
        qs = qs.filter(email_opt_in=True).exclude(
            Q(email__isnull=True) | Q(email="")
        )
    elif campaign_type == "whatsapp_broadcast":
        qs = qs.filter(sms_opt_in=True).exclude(
            Q(phone__isnull=True) | Q(phone="")
        )
    elif campaign_type == "nurture_sequence":
        # Nurture can use both channels, require at least email
        qs = qs.filter(email_opt_in=True).exclude(
            Q(email__isnull=True) | Q(email="")
        )

    # Apply filter criteria
    tags = filter_criteria.get("tags")
    if tags and isinstance(tags, list):
        qs = qs.filter(tags__name__in=tags).distinct()

    source = filter_criteria.get("source")
    if source:
        qs = qs.filter(source=source)

    city = filter_criteria.get("city")
    if city:
        qs = qs.filter(city__icontains=city)

    state = filter_criteria.get("state")
    if state:
        qs = qs.filter(state__icontains=state)

    created_after = filter_criteria.get("created_after")
    if created_after:
        qs = qs.filter(created_at__gte=created_after)

    created_before = filter_criteria.get("created_before")
    if created_before:
        qs = qs.filter(created_at__lte=created_before)

    has_email = filter_criteria.get("has_email")
    if has_email is True:
        qs = qs.exclude(Q(email__isnull=True) | Q(email=""))
    elif has_email is False:
        qs = qs.filter(Q(email__isnull=True) | Q(email=""))

    has_phone = filter_criteria.get("has_phone")
    if has_phone is True:
        qs = qs.exclude(Q(phone__isnull=True) | Q(phone=""))
    elif has_phone is False:
        qs = qs.filter(Q(phone__isnull=True) | Q(phone=""))

    is_active = filter_criteria.get("is_active")
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    return qs
