"""
Duplicate detection service for CRM entities.

Provides methods to find potential duplicate records based on
email, phone, name, and other identifying fields.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accounts.models import Account
    from contacts.models import Contact
    from leads.models import Lead


class DuplicateDetector:
    """Service for detecting potential duplicate records."""

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Normalize a phone number by removing all non-digit characters.
        Returns the last 10 digits for comparison purposes.
        """
        if not phone:
            return ""
        digits_only = re.sub(r"[^\d]", "", phone)
        return digits_only[-10:] if len(digits_only) >= 10 else digits_only

    @staticmethod
    def normalize_domain(website: str) -> str:
        """Extract and normalize domain from a website URL."""
        if not website:
            return ""
        domain = website.lower()
        domain = domain.replace("https://", "").replace("http://", "")
        domain = domain.replace("www.", "")
        domain = domain.split("/")[0]  # Remove path
        return domain

    @classmethod
    def find_duplicate_contacts(
        cls,
        org,
        email: str | None = None,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        exclude_id=None,
    ) -> list["Contact"]:
        """
        Find potential duplicate contacts based on email, phone, or name.

        Returns:
            List of potential duplicate Contact objects
        """
        results = cls.find_duplicate_contacts_with_reasons(
            org, email=email, phone=phone,
            first_name=first_name, last_name=last_name,
            exclude_id=exclude_id,
        )
        return [r["contact"] for r in results]

    @classmethod
    def find_duplicate_contacts_with_reasons(
        cls,
        org,
        email: str | None = None,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        exclude_id=None,
        contact: "Contact | None" = None,
    ) -> list[dict]:
        """
        Find potential duplicate contacts with match reasons.

        If ``contact`` is provided, its fields are used as defaults for
        email/phone/name and additional integration ID checks are performed.

        Returns:
            List of dicts: {"contact": Contact, "match_reasons": [...], "score": int}
        """
        from contacts.models import Contact

        # Use contact fields as defaults
        if contact:
            email = email or contact.email
            phone = phone or contact.phone
            first_name = first_name or contact.first_name
            last_name = last_name or contact.last_name
            if not exclude_id:
                exclude_id = contact.id

        # Collect secondary fields for additional matching
        secondary_email = contact.secondary_email if contact else None
        secondary_phone = contact.secondary_phone if contact else None

        seen: dict[str, list[str]] = {}  # contact.id -> reasons
        base_qs = Contact.objects.filter(org=org, is_active=True)
        if exclude_id:
            base_qs = base_qs.exclude(pk=exclude_id)

        def _add(c, reason):
            cid = str(c.id)
            if cid not in seen:
                seen[cid] = []
            if reason not in seen[cid]:
                seen[cid].append(reason)

        # 1. Email match (primary + secondary + extra_emails)
        if email:
            for c in base_qs.filter(email__iexact=email):
                _add(c, "email")
            # Check secondary_email field
            for c in base_qs.filter(secondary_email__iexact=email):
                _add(c, "email")
            # Also check extra_emails table
            from contacts.models import ContactEmail
            for extra in ContactEmail.objects.filter(
                contact__org=org, email__iexact=email
            ).select_related("contact"):
                if not exclude_id or str(extra.contact_id) != str(exclude_id):
                    _add(extra.contact, "email")

        # 1b. Check secondary_email against other contacts
        if secondary_email:
            for c in base_qs.filter(email__iexact=secondary_email):
                _add(c, "email")
            for c in base_qs.filter(secondary_email__iexact=secondary_email):
                _add(c, "email")

        # 1c. Check if contact has extra_emails that match other contacts' primary emails
        if contact:
            for extra in contact.extra_emails.all():
                for c in base_qs.filter(email__iexact=extra.email):
                    _add(c, "email")

        # 2. Phone match (normalized, primary + secondary + extra_phones)
        if phone:
            normalized = cls.normalize_phone(phone)
            if len(normalized) >= 7:
                for c in base_qs.exclude(phone__isnull=True).exclude(phone=""):
                    if cls.normalize_phone(c.phone) == normalized:
                        _add(c, "phone")
                # Check secondary_phone field
                for c in base_qs.exclude(secondary_phone__isnull=True).exclude(secondary_phone=""):
                    if cls.normalize_phone(c.secondary_phone) == normalized:
                        _add(c, "phone")
                # Also check extra_phones table
                from contacts.models import ContactPhone
                for extra in ContactPhone.objects.filter(
                    contact__org=org,
                ).select_related("contact"):
                    if (
                        cls.normalize_phone(extra.phone) == normalized
                        and (not exclude_id or str(extra.contact_id) != str(exclude_id))
                    ):
                        _add(extra.contact, "phone")

        # 2b. Check secondary_phone against other contacts
        if secondary_phone:
            norm_sec = cls.normalize_phone(secondary_phone)
            if len(norm_sec) >= 7:
                for c in base_qs.exclude(phone__isnull=True).exclude(phone=""):
                    if cls.normalize_phone(c.phone) == norm_sec:
                        _add(c, "phone")
                for c in base_qs.exclude(secondary_phone__isnull=True).exclude(secondary_phone=""):
                    if cls.normalize_phone(c.secondary_phone) == norm_sec:
                        _add(c, "phone")

        # 2c. Check if contact has extra_phones that match other contacts' primary phones
        if contact:
            for extra in contact.extra_phones.all():
                norm_extra = cls.normalize_phone(extra.phone)
                if len(norm_extra) >= 7:
                    for c in base_qs.exclude(phone__isnull=True).exclude(phone=""):
                        if cls.normalize_phone(c.phone) == norm_extra:
                            _add(c, "phone")

        # 3. Name match
        if first_name and last_name:
            for c in base_qs.filter(
                first_name__iexact=first_name, last_name__iexact=last_name
            ):
                _add(c, "name")

        # 4. Integration ID matches (when checking a specific contact)
        if contact:
            # Chatwoot ID in description
            chatwoot_ids = set(
                re.findall(r"chatwoot_id:(\d+)", contact.description or "")
            )
            if chatwoot_ids:
                for cw_id in chatwoot_ids:
                    for c in base_qs.filter(
                        description__contains=f"chatwoot_id:{cw_id}"
                    ):
                        _add(c, "chatwoot_id")

            # TalkHub subscriber ID
            if contact.talkhub_subscriber_id:
                for c in base_qs.filter(
                    talkhub_subscriber_id=contact.talkhub_subscriber_id
                ):
                    _add(c, "talkhub_subscriber_id")

            # Omni user NS
            if contact.omni_user_ns:
                for c in base_qs.filter(omni_user_ns=contact.omni_user_ns):
                    _add(c, "omni_user_ns")

        # Build result list sorted by score desc
        contact_map = {}
        for cid in seen:
            if cid not in contact_map:
                try:
                    contact_map[cid] = base_qs.get(pk=cid)
                except Contact.DoesNotExist:
                    continue

        results = []
        for cid, reasons in seen.items():
            if cid in contact_map:
                results.append({
                    "contact": contact_map[cid],
                    "match_reasons": reasons,
                    "score": len(reasons),
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    @classmethod
    def find_duplicate_leads(
        cls,
        org,
        email: str | None = None,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        exclude_id=None,
    ) -> list["Lead"]:
        """
        Find potential duplicate leads based on email, phone, name, or company.

        Args:
            org: The organization to search within
            email: Email address to match
            phone: Phone number to match (normalized)
            first_name: First name for fuzzy matching
            last_name: Last name for fuzzy matching
            company_name: Company name for fuzzy matching
            exclude_id: ID to exclude from results (for updates)

        Returns:
            List of potential duplicate Lead objects
        """
        from leads.models import Lead

        duplicates = []
        base_qs = Lead.objects.filter(org=org, is_active=True)

        if exclude_id:
            base_qs = base_qs.exclude(pk=exclude_id)

        # Exact email match (case-insensitive)
        if email:
            email_matches = base_qs.filter(email__iexact=email)
            duplicates.extend(list(email_matches))

        # Normalized phone match
        if phone:
            normalized = cls.normalize_phone(phone)
            if len(normalized) >= 7:
                phone_candidates = base_qs.exclude(phone__isnull=True).exclude(phone="")
                for lead in phone_candidates:
                    if cls.normalize_phone(lead.phone) == normalized:
                        if lead not in duplicates:
                            duplicates.append(lead)

        # Name match
        if first_name and last_name:
            name_matches = base_qs.filter(
                first_name__iexact=first_name, last_name__iexact=last_name
            )
            for lead in name_matches:
                if lead not in duplicates:
                    duplicates.append(lead)

        # Company name match (fuzzy - contains)
        if company_name and len(company_name) >= 3:
            company_matches = base_qs.filter(company_name__icontains=company_name)
            for lead in company_matches:
                if lead not in duplicates:
                    duplicates.append(lead)

        return duplicates

    @classmethod
    def find_duplicate_accounts(
        cls,
        org,
        name: str | None = None,
        email: str | None = None,
        website: str | None = None,
        phone: str | None = None,
        exclude_id=None,
    ) -> list["Account"]:
        """
        Find potential duplicate accounts based on name, email, website, or phone.

        Args:
            org: The organization to search within
            name: Account name to match (fuzzy)
            email: Email address to match
            website: Website URL to match (domain normalized)
            phone: Phone number to match (normalized)
            exclude_id: ID to exclude from results (for updates)

        Returns:
            List of potential duplicate Account objects
        """
        from accounts.models import Account

        duplicates = []
        base_qs = Account.objects.filter(org=org, is_active=True)

        if exclude_id:
            base_qs = base_qs.exclude(pk=exclude_id)

        # Exact name match (case-insensitive)
        if name:
            name_matches = base_qs.filter(name__iexact=name)
            duplicates.extend(list(name_matches))

            # Also check for partial matches on first word (for company variations)
            first_word = name.split()[0] if name else ""
            if len(first_word) >= 3:
                partial_matches = base_qs.filter(name__istartswith=first_word).exclude(
                    name__iexact=name
                )
                for account in partial_matches:
                    if account not in duplicates:
                        duplicates.append(account)

        # Exact email match
        if email:
            email_matches = base_qs.filter(email__iexact=email)
            for account in email_matches:
                if account not in duplicates:
                    duplicates.append(account)

        # Website domain match
        if website:
            domain = cls.normalize_domain(website)
            if domain:
                website_candidates = base_qs.exclude(website__isnull=True).exclude(
                    website=""
                )
                for account in website_candidates:
                    if cls.normalize_domain(account.website) == domain:
                        if account not in duplicates:
                            duplicates.append(account)

        # Normalized phone match
        if phone:
            normalized = cls.normalize_phone(phone)
            if len(normalized) >= 7:
                phone_candidates = base_qs.exclude(phone__isnull=True).exclude(phone="")
                for account in phone_candidates:
                    if cls.normalize_phone(account.phone) == normalized:
                        if account not in duplicates:
                            duplicates.append(account)

        return duplicates
