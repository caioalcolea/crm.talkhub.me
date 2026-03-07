from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext

from common.serializer import OrgSettingsSerializer


class OrgSettingsView(APIView):
    """
    API endpoint for org settings (currency, country, locale).

    GET: Returns current org settings
    PATCH: Updates org settings (admin only)
    """

    permission_classes = (IsAuthenticated, HasOrgContext)
    parser_classes = (JSONParser, MultiPartParser)

    def get(self, request):
        """Get current organization settings."""
        org = request.profile.org
        serializer = OrgSettingsSerializer(org, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        """Update organization settings (admin only)."""
        if request.profile.role != "ADMIN" and not request.user.is_superuser:
            return Response(
                {"error": "Only admins can update organization settings"},
                status=status.HTTP_403_FORBIDDEN,
            )

        org = request.profile.org
        serializer = OrgSettingsSerializer(
            org, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
