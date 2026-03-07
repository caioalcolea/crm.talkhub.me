from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Attachments, Comment
from common.permissions import HasOrgContext
from common.serializers import CommentSerializer
from opportunity import swagger_params
from opportunity.models import Opportunity
from opportunity.serializers import OpportunityCommentEditSwaggerSerializer


class OpportunityCommentView(APIView):
    model = Comment
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get_object(self, pk):
        return self.model.objects.get(pk=pk, org=self.request.profile.org)

    def post(self, request, pk, format=None):
        """Create a new comment on an opportunity. pk = opportunity UUID."""
        params = request.data
        comment_text = params.get("comment", "").strip()
        if not comment_text:
            return Response(
                {"error": True, "errors": "Comment text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            opportunity = Opportunity.objects.get(pk=pk, org=request.profile.org)
        except Opportunity.DoesNotExist:
            return Response(
                {"error": True, "errors": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        opportunity_ct = ContentType.objects.get_for_model(Opportunity)
        comment = Comment.objects.create(
            content_type=opportunity_ct,
            object_id=opportunity.id,
            comment=comment_text,
            commented_by=request.profile,
            org=request.profile.org,
        )
        return Response(
            {
                "error": False,
                "message": "Comment Submitted",
                "id": str(comment.id),
                "comment": comment.comment,
                "commented_on": comment.commented_on.isoformat()
                if comment.commented_on
                else None,
                "commented_by": {
                    "id": str(comment.commented_by.id),
                    "user_details": {
                        "email": comment.commented_by.user.email,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


    @extend_schema(
        tags=["Opportunities"],
        parameters=swagger_params.organization_params,
        request=OpportunityCommentEditSwaggerSerializer,
        responses={
            200: inline_serializer(
                name="OpportunityCommentUpdateResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def put(self, request, pk, format=None):
        params = request.data
        obj = self.get_object(pk)
        if (
            request.profile.role == "ADMIN"
            or request.user.is_superuser
            or request.profile == obj.commented_by
        ):
            serializer = CommentSerializer(obj, data=params)
            if params.get("comment"):
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {"error": False, "message": "Comment Submitted"},
                        status=status.HTTP_200_OK,
                    )
                return Response(
                    {"error": True, "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(
            {
                "error": True,
                "errors": "You don't have permission to perform this action.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    @extend_schema(
        tags=["Opportunities"],
        parameters=swagger_params.organization_params,
        request=OpportunityCommentEditSwaggerSerializer,
        description="Partial Comment Update",
        responses={
            200: inline_serializer(
                name="OpportunityCommentPatchResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def patch(self, request, pk, format=None):
        """Handle partial updates to a comment."""
        params = request.data
        obj = self.get_object(pk)
        if (
            request.profile.role == "ADMIN"
            or request.user.is_superuser
            or request.profile == obj.commented_by
        ):
            serializer = CommentSerializer(obj, data=params, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"error": False, "message": "Comment Updated"},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "error": True,
                "errors": "You don't have permission to perform this action.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    @extend_schema(
        tags=["Opportunities"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="OpportunityCommentDeleteResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def delete(self, request, pk, format=None):
        self.object = self.get_object(pk)
        if (
            request.profile.role == "ADMIN"
            or request.user.is_superuser
            or request.profile == self.object.commented_by
        ):
            self.object.delete()
            return Response(
                {"error": False, "message": "Comment Deleted Successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "error": True,
                "errors": "You do not have permission to perform this action",
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class OpportunityAttachmentView(APIView):
    model = Attachments
    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Opportunities"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="OpportunityAttachmentDeleteResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def delete(self, request, pk, format=None):
        self.object = self.model.objects.get(pk=pk)
        if (
            request.profile.role == "ADMIN"
            or request.user.is_superuser
            or request.profile == self.object.created_by
        ):
            self.object.delete()
            return Response(
                {"error": False, "message": "Attachment Deleted Successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "error": True,
                "errors": "You don't have permission to perform this action.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
