import json
from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import HasOrgContext
from rest_framework.views import APIView

from accounts.models import Account
from accounts.serializers import AccountSerializer
from cases import swagger_params
from cases.models import Case
from cases.serializers import (
    CaseCommentEditSwaggerSerializer,
    CaseCreateSerializer,
    CaseCreateSwaggerSerializer,
    CaseDetailEditSwaggerSerializer,
    CaseSerializer,
)
from cases.tasks import send_email_to_assigned_user
from common.models import Attachments, Comment, Profile, Tags, Teams
from common.serializers import AttachmentsSerializer, CommentSerializer
from common.utils import CASE_TYPE, PRIORITY_CHOICE, STATUS_CHOICE
from contacts.models import Contact
from contacts.serializers import ContactSerializer
from tasks.models import Subtask
from tasks.serializers import SubtaskSerializer


class CaseListView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated, HasOrgContext)
    model = Case

    def get_context_data(self, **kwargs):
        params = self.request.query_params
        queryset = self.model.objects.filter(org=self.request.profile.org).select_related(
            "account", "org"
        ).prefetch_related(
            "contacts", "assigned_to", "teams", "tags"
        ).order_by(
            "-id"
        )
        accounts = Account.objects.filter(org=self.request.profile.org).order_by("-id")
        contacts = Contact.objects.filter(org=self.request.profile.org).order_by("-id")
        profiles = Profile.objects.filter(is_active=True, org=self.request.profile.org)
        if self.request.profile.role != "ADMIN" and not self.request.profile.is_admin:
            queryset = queryset.filter(
                Q(created_by=self.request.profile.user)
                | Q(assigned_to=self.request.profile)
            ).distinct()
            accounts = accounts.filter(
                Q(created_by=self.request.profile.user)
                | Q(assigned_to=self.request.profile)
            ).distinct()
            contacts = contacts.filter(
                Q(created_by=self.request.profile.user)
                | Q(assigned_to=self.request.profile)
            ).distinct()
            profiles = profiles.filter(role="ADMIN")

        if params:
            if params.get("name"):
                queryset = queryset.filter(name__icontains=params.get("name"))
            if params.get("status"):
                queryset = queryset.filter(status=params.get("status"))
            if params.get("priority"):
                queryset = queryset.filter(priority=params.get("priority"))
            if params.get("account"):
                queryset = queryset.filter(account=params.get("account"))
            if params.get("case_type"):
                queryset = queryset.filter(case_type=params.get("case_type"))
            if params.getlist("assigned_to"):
                queryset = queryset.filter(
                    assigned_to__id__in=params.getlist("assigned_to")
                ).distinct()
            if params.get("tags"):
                queryset = queryset.filter(
                    tags__id__in=params.getlist("tags")
                ).distinct()
            if params.get("search"):
                queryset = queryset.filter(name__icontains=params.get("search"))
            if params.get("created_at__gte"):
                queryset = queryset.filter(
                    created_at__gte=params.get("created_at__gte")
                )
            if params.get("created_at__lte"):
                queryset = queryset.filter(
                    created_at__lte=params.get("created_at__lte")
                )
            if params.get("due_date__gte"):
                queryset = queryset.filter(due_date__gte=params.get("due_date__gte"))
            if params.get("due_date__lte"):
                queryset = queryset.filter(due_date__lte=params.get("due_date__lte"))

            # Quick filters
            quick_filter = params.get("quick_filter")
            if quick_filter:
                today = date.today()
                if quick_filter == "overdue":
                    queryset = queryset.filter(
                        due_date__lt=today,
                    ).exclude(
                        status__in=["Closed", "Rejected", "Duplicate"],
                    )
                elif quick_filter == "due_today":
                    queryset = queryset.filter(due_date=today)
                elif quick_filter == "due_this_week":
                    monday = today - timedelta(days=today.weekday())
                    sunday = monday + timedelta(days=6)
                    queryset = queryset.filter(due_date__range=[monday, sunday])
                elif quick_filter == "completed_this_week":
                    monday = today - timedelta(days=today.weekday())
                    queryset = queryset.filter(
                        status="Closed",
                        updated_at__gte=monday,
                    )
                elif quick_filter == "no_date":
                    queryset = queryset.filter(
                        due_date__isnull=True,
                    ).exclude(
                        status__in=["Closed", "Rejected", "Duplicate"],
                    )
                elif quick_filter == "open":
                    queryset = queryset.filter(
                        status__in=["New", "Assigned", "Pending"]
                    )
                elif quick_filter == "closed":
                    queryset = queryset.filter(
                        status__in=["Closed", "Rejected", "Duplicate"]
                    )

        context = {}

        results_cases = self.paginate_queryset(queryset, self.request, view=self)
        cases = CaseSerializer(results_cases, many=True).data

        if results_cases:
            offset = queryset.filter(id__gte=results_cases[-1].id).count()
            if offset == queryset.count():
                offset = None
        else:
            offset = 0
        context.update(
            {
                "cases_count": self.count,
                "offset": offset,
            }
        )
        context["cases"] = cases
        context["status"] = STATUS_CHOICE
        context["priority"] = PRIORITY_CHOICE
        context["type_of_case"] = CASE_TYPE
        context["accounts_list"] = AccountSerializer(accounts, many=True).data
        context["contacts_list"] = ContactSerializer(contacts, many=True).data
        return context

    @extend_schema(
        operation_id="cases_list",
        tags=["Cases"],
        parameters=swagger_params.cases_list_get_params,
        responses={
            200: inline_serializer(
                name="CaseListResponse",
                fields={
                    "cases_count": serializers.IntegerField(),
                    "offset": serializers.IntegerField(allow_null=True),
                    "cases": CaseSerializer(many=True),
                    "status": serializers.ListField(),
                    "priority": serializers.ListField(),
                    "type_of_case": serializers.ListField(),
                    "accounts_list": AccountSerializer(many=True),
                    "contacts_list": ContactSerializer(many=True),
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return Response(context)

    @extend_schema(
        operation_id="cases_create",
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        request=CaseCreateSwaggerSerializer,
        responses={
            200: inline_serializer(
                name="CaseCreateResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                    "id": serializers.CharField(),
                    "cases_obj": CaseSerializer(),
                },
            )
        },
    )
    def post(self, request, *args, **kwargs):
        params = request.data
        serializer = CaseCreateSerializer(data=params, request_obj=request)
        if serializer.is_valid():
            cases_obj = serializer.save(
                created_by=request.profile.user,
                org=request.profile.org,
                closed_on=params.get("closed_on"),
                case_type=params.get("case_type"),
            )

            if params.get("contacts"):
                contacts_list = params.get("contacts")
                if isinstance(contacts_list, str):
                    contacts_list = json.loads(contacts_list)
                # Extract IDs if contacts_list contains objects with 'id' field
                contact_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in contacts_list
                ]
                contacts = Contact.objects.filter(
                    id__in=contact_ids, org=request.profile.org
                )
                if contacts:
                    cases_obj.contacts.add(*contacts)

            if params.get("teams"):
                teams_list = params.get("teams")
                if isinstance(teams_list, str):
                    teams_list = json.loads(teams_list)
                # Extract IDs if teams_list contains objects with 'id' field
                team_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in teams_list
                ]
                teams = Teams.objects.filter(id__in=team_ids, org=request.profile.org)
                if teams.exists():
                    cases_obj.teams.add(*teams)

            if params.get("assigned_to"):
                assinged_to_list = params.get("assigned_to")
                if isinstance(assinged_to_list, str):
                    assinged_to_list = json.loads(assinged_to_list)
                # Extract IDs if assinged_to_list contains objects with 'id' field
                assigned_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in assinged_to_list
                ]
                profiles = Profile.objects.filter(
                    id__in=assigned_ids, org=request.profile.org, is_active=True
                )
                if profiles:
                    cases_obj.assigned_to.add(*profiles)

            if params.get("tags"):
                tags = params.get("tags")
                if isinstance(tags, str):
                    tags = json.loads(tags)
                # Extract IDs if tags contains objects with 'id' field
                tag_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in tags
                ]
                tag_objs = Tags.objects.filter(
                    id__in=tag_ids, org=request.profile.org, is_active=True
                )
                cases_obj.tags.add(*tag_objs)

            if self.request.FILES.get("case_attachment"):
                attachment = Attachments()
                attachment.created_by = self.request.profile.user
                attachment.file_name = self.request.FILES.get("case_attachment").name
                attachment.content_object = cases_obj
                attachment.attachment = self.request.FILES.get("case_attachment")
                attachment.org = self.request.profile.org
                attachment.save()

            recipients = list(cases_obj.assigned_to.all().values_list("id", flat=True))
            send_email_to_assigned_user.delay(
                recipients,
                cases_obj.id,
                str(request.profile.org.id),
            )
            return Response(
                {
                    "error": False,
                    "message": "Case Created Successfully",
                    "id": str(cases_obj.id),
                    "cases_obj": CaseSerializer(cases_obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class CaseDetailView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)
    model = Case

    def get_object(self, pk):
        return self.model.objects.filter(id=pk, org=self.request.profile.org).first()

    @extend_schema(
        operation_id="cases_update",
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        request=CaseCreateSwaggerSerializer,
        responses={
            200: inline_serializer(
                name="CaseUpdateResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def put(self, request, pk, format=None):
        params = request.data
        cases_object = self.get_object(pk=pk)
        if cases_object.org != request.profile.org:
            return Response(
                {"error": True, "errors": "User company doesnot match with header...."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if self.request.profile.role != "ADMIN" and not self.request.profile.is_admin:
            if not (
                (self.request.profile.user == cases_object.created_by)
                or (self.request.profile in cases_object.assigned_to.all())
            ):
                return Response(
                    {
                        "error": True,
                        "errors": "You do not have Permission to perform this action",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = CaseCreateSerializer(
            cases_object,
            data=params,
            request_obj=request,
        )

        if serializer.is_valid():
            cases_object = serializer.save(
                closed_on=params.get("closed_on"), case_type=params.get("case_type")
            )
            previous_assigned_to_users = list(
                cases_object.assigned_to.all().values_list("id", flat=True)
            )
            cases_object.contacts.clear()
            if params.get("contacts"):
                contacts_list = params.get("contacts")
                if isinstance(contacts_list, str):
                    contacts_list = json.loads(contacts_list)
                # Extract IDs if contacts_list contains objects with 'id' field
                contact_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in contacts_list
                ]
                contacts = Contact.objects.filter(
                    id__in=contact_ids, org=request.profile.org
                )
                if contacts:
                    cases_object.contacts.add(*contacts)

            cases_object.teams.clear()
            if params.get("teams"):
                teams_list = params.get("teams")
                if isinstance(teams_list, str):
                    teams_list = json.loads(teams_list)
                # Extract IDs if teams_list contains objects with 'id' field
                team_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in teams_list
                ]
                teams = Teams.objects.filter(id__in=team_ids, org=request.profile.org)
                if teams.exists():
                    cases_object.teams.add(*teams)

            cases_object.assigned_to.clear()
            if params.get("assigned_to"):
                assinged_to_list = params.get("assigned_to")
                if isinstance(assinged_to_list, str):
                    assinged_to_list = json.loads(assinged_to_list)
                # Extract IDs if assinged_to_list contains objects with 'id' field
                assigned_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in assinged_to_list
                ]
                profiles = Profile.objects.filter(
                    id__in=assigned_ids, org=request.profile.org, is_active=True
                )
                if profiles:
                    cases_object.assigned_to.add(*profiles)

            cases_object.tags.clear()
            if params.get("tags"):
                tags = params.get("tags")
                if isinstance(tags, str):
                    tags = json.loads(tags)
                # Extract IDs if tags contains objects with 'id' field
                tag_ids = [
                    item.get("id") if isinstance(item, dict) else item
                    for item in tags
                ]
                tag_objs = Tags.objects.filter(
                    id__in=tag_ids, org=request.profile.org, is_active=True
                )
                cases_object.tags.add(*tag_objs)

            if self.request.FILES.get("case_attachment"):
                attachment = Attachments()
                attachment.created_by = self.request.profile.user
                attachment.file_name = self.request.FILES.get("case_attachment").name
                attachment.content_object = cases_object
                attachment.attachment = self.request.FILES.get("case_attachment")
                attachment.org = self.request.profile.org
                attachment.save()

            assigned_to_list = list(
                cases_object.assigned_to.all().values_list("id", flat=True)
            )
            recipients = list(set(assigned_to_list) - set(previous_assigned_to_users))
            send_email_to_assigned_user.delay(
                recipients,
                cases_object.id,
                str(request.profile.org.id),
            )
            return Response(
                {"error": False, "message": "Case Updated Successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(
        operation_id="cases_destroy",
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="CaseDeleteResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def delete(self, request, pk, format=None):
        self.object = self.get_object(pk)
        if self.object.org != request.profile.org:
            return Response(
                {"error": True, "errors": "User company doesnot match with header...."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if self.request.profile.role != "ADMIN" and not self.request.profile.is_admin:
            if self.request.profile.user != self.object.created_by:
                return Response(
                    {
                        "error": True,
                        "errors": "You do not have Permission to perform this action",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        self.object.delete()
        return Response(
            {"error": False, "message": "Case Deleted Successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="cases_retrieve",
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="CaseDetailResponse",
                fields={
                    "cases_obj": CaseSerializer(),
                    "attachments": AttachmentsSerializer(many=True),
                    "comments": CommentSerializer(many=True),
                    "comment_permission": serializers.BooleanField(),
                    "users_mention": serializers.ListField(),
                },
            )
        },
    )
    def get(self, request, pk, format=None):
        self.cases = self.get_object(pk=pk)
        if not self.cases:
            return Response(
                {"error": True, "errors": "Case not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if self.cases.org != request.profile.org:
            return Response(
                {"error": True, "errors": "User company doesnot match with header...."},
                status=status.HTTP_403_FORBIDDEN,
            )
        context = {}
        context["cases_obj"] = CaseSerializer(self.cases).data
        if self.request.profile.role != "ADMIN" and not self.request.profile.is_admin:
            if not (
                (self.request.profile.user == self.cases.created_by)
                or (self.request.profile in self.cases.assigned_to.all())
            ):
                return Response(
                    {
                        "error": True,
                        "errors": "You don't have Permission to perform this action",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        comment_permission = False

        if (
            self.request.profile.user == self.cases.created_by
            or self.request.profile.is_admin
            or self.request.profile.role == "ADMIN"
        ):
            comment_permission = True

        if self.request.profile.is_admin or self.request.profile.role == "ADMIN":
            users_mention = list(
                Profile.objects.filter(
                    is_active=True, org=self.request.profile.org
                ).values("user__email")
            )
        elif self.request.profile != self.cases.created_by:
            if self.cases.created_by:
                users_mention = [{"username": self.cases.created_by.user.email}]
            else:
                users_mention = []
        else:
            users_mention = []

        case_content_type = ContentType.objects.get_for_model(Case)
        attachments = Attachments.objects.filter(
            content_type=case_content_type,
            object_id=self.cases.id,
            org=self.request.profile.org,
        ).order_by("-id")
        comments = Comment.objects.filter(
            content_type=case_content_type,
            object_id=self.cases.id,
            org=self.request.profile.org,
        ).order_by("-id")

        context.update(
            {
                "attachments": AttachmentsSerializer(attachments, many=True).data,
                "comments": CommentSerializer(comments, many=True).data,
                "contacts": ContactSerializer(
                    self.cases.contacts.all(), many=True
                ).data,
                "linked_tasks": self._get_linked_tasks(self.cases),
                "status": STATUS_CHOICE,
                "priority": PRIORITY_CHOICE,
                "type_of_case": CASE_TYPE,
                "comment_permission": comment_permission,
                "users_mention": users_mention,
            }
        )
        return Response(context)

    def _get_linked_tasks(self, case):
        """Return lightweight list of tasks linked to this case."""
        from tasks.models import Task
        tasks = Task.objects.filter(case=case).values(
            "id", "title", "status", "priority", "due_date", "created_at",
        ).order_by("-created_at")[:20]
        return list(tasks)

    @extend_schema(
        operation_id="cases_comment_attachment",
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        request=CaseDetailEditSwaggerSerializer,
        responses={
            200: inline_serializer(
                name="CaseCommentAttachmentResponse",
                fields={
                    "cases_obj": CaseSerializer(),
                    "attachments": AttachmentsSerializer(many=True),
                    "comments": CommentSerializer(many=True),
                },
            )
        },
    )
    def post(self, request, pk, **kwargs):
        params = request.data
        self.cases_obj = Case.objects.get(pk=pk, org=request.profile.org)
        if self.cases_obj.org != request.profile.org:
            return Response(
                {"error": True, "errors": "User company doesnot match with header...."},
                status=status.HTTP_403_FORBIDDEN,
            )
        context = {}
        comment_serializer = CommentSerializer(data=params)
        if self.request.profile.role != "ADMIN" and not self.request.profile.is_admin:
            if not (
                (self.request.profile.user == self.cases_obj.created_by)
                or (self.request.profile in self.cases_obj.assigned_to.all())
            ):
                return Response(
                    {
                        "error": True,
                        "errors": "You don't have Permission to perform this action",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        if comment_serializer.is_valid():
            if params.get("comment"):
                comment_serializer.save(
                    case_id=self.cases_obj.id,
                    commented_by_id=self.request.profile.id,
                )

        if self.request.FILES.get("case_attachment"):
            attachment = Attachments()
            attachment.created_by = self.request.profile.user
            attachment.file_name = self.request.FILES.get("case_attachment").name
            attachment.content_object = self.cases_obj
            attachment.attachment = self.request.FILES.get("case_attachment")
            attachment.org = self.request.profile.org
            attachment.save()

        case_content_type = ContentType.objects.get_for_model(Case)
        attachments = Attachments.objects.filter(
            content_type=case_content_type,
            object_id=self.cases_obj.id,
            org=request.profile.org,
        ).order_by("-id")
        comments = Comment.objects.filter(
            content_type=case_content_type,
            object_id=self.cases_obj.id,
            org=request.profile.org,
        ).order_by("-id")

        context.update(
            {
                "cases_obj": CaseSerializer(self.cases_obj).data,
                "attachments": AttachmentsSerializer(attachments, many=True).data,
                "comments": CommentSerializer(comments, many=True).data,
            }
        )
        return Response(context)

    @extend_schema(
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        request=CaseCreateSwaggerSerializer,
        description="Partial Case Update",
        responses={
            200: inline_serializer(
                name="CasePatchResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def patch(self, request, pk, format=None):
        """Handle partial updates to a case."""
        params = request.data
        cases_object = self.get_object(pk=pk)
        if cases_object.org != request.profile.org:
            return Response(
                {
                    "error": True,
                    "errors": "User company does not match with header....",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if self.request.profile.role != "ADMIN" and not self.request.profile.is_admin:
            if not (
                (self.request.profile.user == cases_object.created_by)
                or (self.request.profile in cases_object.assigned_to.all())
            ):
                return Response(
                    {
                        "error": True,
                        "errors": "You do not have Permission to perform this action",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = CaseCreateSerializer(
            cases_object,
            data=params,
            request_obj=request,
            partial=True,
        )

        if serializer.is_valid():
            cases_object = serializer.save(
                closed_on=params.get("closed_on")
                if "closed_on" in params
                else cases_object.closed_on,
                case_type=params.get("case_type")
                if "case_type" in params
                else cases_object.case_type,
            )

            # Handle M2M fields if present in request
            if "contacts" in params:
                cases_object.contacts.clear()
                contacts_list = params.get("contacts")
                if contacts_list:
                    if isinstance(contacts_list, str):
                        contacts_list = json.loads(contacts_list)
                    # Extract IDs if contacts_list contains objects with 'id' field
                    contact_ids = [
                        item.get("id") if isinstance(item, dict) else item
                        for item in contacts_list
                    ]
                    contacts = Contact.objects.filter(
                        id__in=contact_ids, org=request.profile.org
                    )
                    cases_object.contacts.add(*contacts)

            if "teams" in params:
                cases_object.teams.clear()
                teams_list = params.get("teams")
                if teams_list:
                    if isinstance(teams_list, str):
                        teams_list = json.loads(teams_list)
                    # Extract IDs if teams_list contains objects with 'id' field
                    team_ids = [
                        item.get("id") if isinstance(item, dict) else item
                        for item in teams_list
                    ]
                    teams = Teams.objects.filter(
                        id__in=team_ids, org=request.profile.org
                    )
                    cases_object.teams.add(*teams)

            if "assigned_to" in params:
                cases_object.assigned_to.clear()
                assigned_to_list = params.get("assigned_to")
                if assigned_to_list:
                    if isinstance(assigned_to_list, str):
                        assigned_to_list = json.loads(assigned_to_list)
                    # Extract IDs if assigned_to_list contains objects with 'id' field
                    assigned_ids = [
                        item.get("id") if isinstance(item, dict) else item
                        for item in assigned_to_list
                    ]
                    profiles = Profile.objects.filter(
                        id__in=assigned_ids, org=request.profile.org, is_active=True
                    )
                    cases_object.assigned_to.add(*profiles)

            if "tags" in params:
                cases_object.tags.clear()
                tags_list = params.get("tags")
                if tags_list:
                    if isinstance(tags_list, str):
                        tags_list = json.loads(tags_list)
                    # Extract IDs if tags_list contains objects with 'id' field
                    tag_ids = [
                        tag.get("id") if isinstance(tag, dict) else tag
                        for tag in tags_list
                    ]
                    tag_objs = Tags.objects.filter(
                        id__in=tag_ids, org=request.profile.org, is_active=True
                    )
                    cases_object.tags.add(*tag_objs)

            return Response(
                {"error": False, "message": "Case Updated Successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class CaseCommentView(APIView):
    model = Comment
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get_object(self, pk):
        return self.model.objects.get(pk=pk, org=self.request.profile.org)

    def post(self, request, pk, format=None):
        """Create a new comment on a case. pk = case UUID."""
        params = request.data
        comment_text = params.get("comment", "").strip()
        if not comment_text:
            return Response(
                {"error": True, "errors": "Comment text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            case = Case.objects.get(pk=pk, org=request.profile.org)
        except Case.DoesNotExist:
            return Response(
                {"error": True, "errors": "Case not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        case_ct = ContentType.objects.get_for_model(Case)
        comment = Comment.objects.create(
            content_type=case_ct,
            object_id=case.id,
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
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        request=CaseCommentEditSwaggerSerializer,
        responses={
            200: inline_serializer(
                name="CaseCommentUpdateResponse",
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
            or request.profile.is_admin
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
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        request=CaseCommentEditSwaggerSerializer,
        description="Partial Comment Update",
        responses={
            200: inline_serializer(
                name="CaseCommentPatchResponse",
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
            or request.profile.is_admin
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
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="CaseCommentDeleteResponse",
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
            or request.profile.is_admin
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


class CaseAttachmentView(APIView):
    model = Attachments
    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["Cases"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="CaseAttachmentDeleteResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def delete(self, request, pk, format=None):
        try:
            self.object = self.model.objects.get(pk=pk, org=request.profile.org)
        except self.model.DoesNotExist:
            return Response(
                {"error": True, "errors": "Attachment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if (
            request.profile.role == "ADMIN"
            or request.profile.is_admin
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


class CaseTaskCreateView(APIView):
    """Create a Task pre-linked to a Case."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        operation_id="case_create_task",
        tags=["Cases"],
        parameters=swagger_params.organization_params,
    )
    def post(self, request, pk):
        from tasks.models import Task
        from tasks.serializers import TaskCreateSerializer, TaskSerializer

        org = request.profile.org
        case = Case.objects.filter(pk=pk, org=org).first()
        if not case:
            return Response(
                {"error": True, "errors": "Case not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()
        data["case"] = str(case.id)

        serializer = TaskCreateSerializer(data=data, request_obj=request)
        if serializer.is_valid():
            task = serializer.save(
                created_by=request.profile.user,
                org=org,
            )
            return Response(
                {
                    "error": False,
                    "message": "Task created and linked to case",
                    "task": TaskSerializer(task).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class CaseRelatedView(APIView):
    """
    GET /api/cases/{id}/related/?include=tasks
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, pk):
        org = request.profile.org
        include = set(request.query_params.get("include", "").split(","))
        context = {}

        if "tasks" in include:
            from tasks.models import Task

            qs = Task.objects.filter(case_id=pk, org=org).exclude(
                status="Completed"
            )
            context["tasks_count"] = qs.count()
            context["tasks"] = [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status,
                    "due_date": str(t.due_date) if t.due_date else None,
                    "priority": t.priority,
                }
                for t in qs.order_by("-created_at")[:5]
            ]

        return Response(context)


class CaseSubtaskListCreateView(APIView):
    """GET/POST subtasks for a case."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, pk):
        org = request.profile.org
        case = Case.objects.filter(pk=pk, org=org).first()
        if not case:
            return Response(
                {"error": True, "errors": "Case not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        subtasks = Subtask.objects.filter(case=case, org=org).order_by("order", "created_at")
        return Response(SubtaskSerializer(subtasks, many=True).data)

    def post(self, request, pk):
        org = request.profile.org
        case = Case.objects.filter(pk=pk, org=org).first()
        if not case:
            return Response(
                {"error": True, "errors": "Case not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data
        max_order = Subtask.objects.filter(case=case).count()
        subtask = Subtask.objects.create(
            case=case,
            title=data.get("title", ""),
            order=data.get("order", max_order),
            org=org,
            created_by=request.profile.user,
        )
        return Response(
            SubtaskSerializer(subtask).data,
            status=status.HTTP_201_CREATED,
        )


class CaseSubtaskDetailView(APIView):
    """PATCH/DELETE a case subtask."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def patch(self, request, pk):
        org = request.profile.org
        subtask = Subtask.objects.filter(pk=pk, case__isnull=False, org=org).first()
        if not subtask:
            return Response(
                {"error": True, "errors": "Subtask not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data
        if "title" in data:
            subtask.title = data["title"]
        if "is_completed" in data:
            subtask.is_completed = data["is_completed"]
            if data["is_completed"]:
                subtask.completed_at = timezone.now()
                subtask.completed_by = request.profile.user
            else:
                subtask.completed_at = None
                subtask.completed_by = None
        if "order" in data:
            subtask.order = data["order"]
        subtask.save()
        return Response(SubtaskSerializer(subtask).data)

    def delete(self, request, pk):
        org = request.profile.org
        subtask = Subtask.objects.filter(pk=pk, case__isnull=False, org=org).first()
        if not subtask:
            return Response(
                {"error": True, "errors": "Subtask not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        subtask.delete()
        return Response(
            {"error": False, "message": "Subtask deleted"},
            status=status.HTTP_200_OK,
        )


class CaseWorkloadView(APIView):
    """GET /cases/workload/ — case counts per user with SLA metrics."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        org = request.profile.org
        today = date.today()
        period = request.query_params.get("period", "week")

        if period == "month":
            period_start = today.replace(day=1)
        else:
            period_start = today - timedelta(days=today.weekday())

        profiles = Profile.objects.filter(org=org, is_active=True)
        result = []

        for profile in profiles.select_related("user"):
            cases_qs = Case.objects.filter(org=org, assigned_to=profile)
            active_cases = list(
                cases_qs.exclude(status__in=["Closed", "Rejected", "Duplicate"])
            )
            total = len(active_cases)
            open_count = cases_qs.filter(status__in=["New", "Assigned"]).count()
            pending_count = cases_qs.filter(status="Pending").count()
            sla_breached = sum(
                1
                for c in active_cases
                if c.is_sla_first_response_breached
                or c.is_sla_resolution_breached
            )
            resolved_this_period = cases_qs.filter(
                status="Closed",
                updated_at__gte=period_start,
            ).count()

            result.append({
                "user": {
                    "id": str(profile.id),
                    "name": str(profile),
                    "email": profile.user.email,
                },
                "counts": {
                    "total": total,
                    "open": open_count,
                    "pending": pending_count,
                    "sla_breached": sla_breached,
                    "resolved_this_period": resolved_this_period,
                },
            })

        result.sort(key=lambda x: x["counts"]["total"], reverse=True)
        return Response({"workload": result, "period": period})


class CaseSLADashboardView(APIView):
    """GET /cases/sla-dashboard/ — SLA metrics overview."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        org = request.profile.org
        open_cases_qs = Case.objects.filter(org=org).exclude(
            status__in=["Closed", "Rejected", "Duplicate"]
        )
        open_cases_list = list(open_cases_qs)
        total_open = len(open_cases_list)

        # SLA breach check uses @property — must filter in Python
        sla_breached_count = sum(
            1
            for c in open_cases_list
            if c.is_sla_first_response_breached
            or c.is_sla_resolution_breached
        )

        # At-risk: >75% of SLA time used but not yet breached
        sla_at_risk_count = 0
        now = timezone.now()
        for case in open_cases_list:
            if (
                not case.is_sla_resolution_breached
                and case.sla_resolution_hours
                and case.sla_resolution_hours > 0
                and case.created_at
            ):
                elapsed = (now - case.created_at).total_seconds() / 3600
                threshold = case.sla_resolution_hours * 0.75
                if elapsed >= threshold:
                    sla_at_risk_count += 1

        # Average response/resolution times (from closed cases)
        closed_cases = Case.objects.filter(org=org, status="Closed")
        avg_first_response = None
        avg_resolution = None
        cases_with_response = closed_cases.filter(first_response_at__isnull=False)
        if cases_with_response.exists():
            sample = list(cases_with_response[:100])
            total_hours = sum(
                (c.first_response_at - c.created_at).total_seconds() / 3600
                for c in sample
            )
            avg_first_response = round(total_hours / len(sample), 1)

        cases_with_resolution = closed_cases.filter(resolved_at__isnull=False)
        if cases_with_resolution.exists():
            sample = list(cases_with_resolution[:100])
            total_hours = sum(
                (c.resolved_at - c.created_at).total_seconds() / 3600
                for c in sample
            )
            avg_resolution = round(total_hours / len(sample), 1)

        # By priority — use Python filtering since SLA breach is a @property
        by_priority = []
        for priority in ["Low", "Normal", "High", "Urgent"]:
            priority_cases = [c for c in open_cases_list if c.priority == priority]
            breached = sum(
                1
                for c in priority_cases
                if c.is_sla_first_response_breached
                or c.is_sla_resolution_breached
            )
            by_priority.append({
                "priority": priority,
                "count": len(priority_cases),
                "breached": breached,
            })

        escalated_count = sum(
            1 for c in open_cases_list if (c.escalation_level or 0) > 0
        )

        return Response({
            "total_open": total_open,
            "sla_breached_count": sla_breached_count,
            "sla_at_risk_count": sla_at_risk_count,
            "avg_first_response_hours": avg_first_response,
            "avg_resolution_hours": avg_resolution,
            "by_priority": by_priority,
            "escalated_count": escalated_count,
        })
