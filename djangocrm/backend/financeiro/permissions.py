from rest_framework.permissions import BasePermission


class HasFinancialAccess(BasePermission):
    """
    Permission check for Financeiro module.

    ADMIN role and org admins always have access.
    Other users need has_financial_access=True on their profile.
    """

    message = "Você não tem acesso ao módulo Financeiro."

    def has_permission(self, request, view):
        if not hasattr(request, "profile") or not request.profile:
            return False

        profile = request.profile

        # ADMIN role or org admin always has access
        if profile.role == "ADMIN" or profile.is_organization_admin:
            return True

        return getattr(profile, "has_financial_access", False)
