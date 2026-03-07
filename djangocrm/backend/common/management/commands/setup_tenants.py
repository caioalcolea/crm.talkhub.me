"""
Management command to create organizations and their admin users.

Usage:
    python manage.py setup_tenants

Creates:
    - Organization "TalkHub" with user caio@talkhub.me
    - Organization "Mutual" with user caio@mutual.com.br
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection

from common.models import Org, Profile

User = get_user_model()

TENANTS = [
    {
        "org_name": "TalkHub",
        "company_name": "TalkHub Tecnologia",
        "email": "caio@talkhub.me",
        "password": "TalkHub2026!",
        "currency": "BRL",
        "country": "BR",
    },
    {
        "org_name": "Mutual",
        "company_name": "Mutual Seguros",
        "email": "caio@mutual.com.br",
        "password": "TalkHub2026!",
        "currency": "BRL",
        "country": "BR",
    },
]


class Command(BaseCommand):
    help = "Create tenant organizations and their admin users"

    def handle(self, *args, **options):
        # Bypass RLS for this admin operation (use superuser connection)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_org', '', false)")

        for tenant in TENANTS:
            self._create_tenant(tenant)

        self.stdout.write(self.style.SUCCESS("\nAll tenants created successfully!"))
        self.stdout.write("")
        self.stdout.write("Login at: https://crm.talkhub.me/login")
        for t in TENANTS:
            self.stdout.write(f"  {t['org_name']}: {t['email']} / {t['password']}")

    def _create_tenant(self, tenant):
        org_name = tenant["org_name"]
        email = tenant["email"]

        # 1. Create or get organization
        org, org_created = Org.objects.get_or_create(
            name=org_name,
            defaults={
                "company_name": tenant["company_name"],
                "default_currency": tenant["currency"],
                "default_country": tenant["country"],
                "is_active": True,
            },
        )
        if org_created:
            self.stdout.write(self.style.SUCCESS(f"  Created org: {org_name} (id={org.id})"))
        else:
            self.stdout.write(f"  Org already exists: {org_name} (id={org.id})")

        # 2. Create or get user
        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
                "is_staff": True,
            },
        )
        if user_created:
            user.set_password(tenant["password"])
            user.save()
            self.stdout.write(self.style.SUCCESS(f"  Created user: {email}"))
        else:
            self.stdout.write(f"  User already exists: {email}")

        # 3. Create or get profile (links user to org)
        profile, profile_created = Profile.objects.get_or_create(
            user=user,
            org=org,
            defaults={
                "role": "ADMIN",
                "is_organization_admin": True,
                "has_sales_access": True,
                "has_marketing_access": True,
                "is_active": True,
            },
        )
        if profile_created:
            self.stdout.write(
                self.style.SUCCESS(f"  Created profile: {email} -> {org_name} (ADMIN)")
            )
        else:
            self.stdout.write(f"  Profile already exists: {email} -> {org_name}")
