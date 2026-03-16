"""
Views do app campaigns.

- CampaignListCreateView: GET / POST campanhas.
- CampaignDetailView: GET / PATCH / DELETE campanha.
- CampaignAudienceListCreateView: GET / POST audiências de uma campanha.
- CampaignAudiencePreviewView: POST preview de audiência (contagem sem criar).
- CampaignAudienceGenerateView: POST gerar recipients a partir de audiência.
- CampaignRecipientListView: GET recipients de uma campanha.
- CampaignStepListCreateView: GET / POST steps de uma campanha.
- CampaignStepDetailView: GET / PATCH / DELETE step.
- CampaignAnalyticsView: GET analytics de uma campanha.
- CampaignScheduleView: POST agendar campanha.
- CampaignPauseResumeView: POST pausar/retomar campanha.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext

from campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignRecipient,
    CampaignStep,
)
from campaigns.serializers import (
    CampaignAudienceSerializer,
    CampaignAudienceWriteSerializer,
    CampaignRecipientSerializer,
    CampaignSerializer,
    CampaignStepSerializer,
    CampaignStepWriteSerializer,
    CampaignWriteSerializer,
)


class CampaignListCreateView(APIView):
    """Listar e criar campanhas da organização."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        qs = Campaign.objects.for_org(request.org)

        campaign_type = request.query_params.get("type")
        if campaign_type:
            qs = qs.filter(campaign_type=campaign_type)

        campaign_status = request.query_params.get("status")
        if campaign_status:
            qs = qs.filter(status=campaign_status)

        serializer = CampaignSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CampaignWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.org)
        return Response(
            CampaignSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


class CampaignDetailView(APIView):
    """Detalhe, atualização e exclusão de campanha."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def _get_campaign(self, request, pk):
        try:
            return Campaign.objects.for_org(request.org).get(pk=pk)
        except Campaign.DoesNotExist:
            return None

    def get(self, request, pk):
        campaign = self._get_campaign(request, pk)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CampaignSerializer(campaign).data)

    def patch(self, request, pk):
        campaign = self._get_campaign(request, pk)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CampaignWriteSerializer(
            campaign, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CampaignSerializer(serializer.instance).data)

    def delete(self, request, pk):
        campaign = self._get_campaign(request, pk)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if campaign.status == "running":
            return Response(
                {"error": "Não é possível excluir campanha em execução."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampaignAudienceListCreateView(APIView):
    """Listar e criar audiências de uma campanha."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def _get_campaign(self, request, campaign_id):
        try:
            return Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return None

    def get(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = CampaignAudience.objects.filter(campaign=campaign, org=request.org)
        serializer = CampaignAudienceSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CampaignAudienceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.org, campaign=campaign)
        return Response(
            CampaignAudienceSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


class CampaignAudiencePreviewView(APIView):
    """Preview de audiência: retorna contagem sem criar recipients."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, campaign_id):
        from campaigns.audience import build_audience_queryset

        try:
            campaign = Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        filter_criteria = request.data.get("filter_criteria", {})
        qs = build_audience_queryset(request.org, campaign.campaign_type, filter_criteria)
        count = qs.count()

        return Response({"count": count, "filter_criteria": filter_criteria})


class CampaignAudienceGenerateView(APIView):
    """Gerar CampaignRecipients a partir de critérios de audiência."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, campaign_id):
        from campaigns.audience import build_audience_queryset

        try:
            campaign = Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if campaign.status not in ("draft", "scheduled"):
            return Response(
                {"error": "Só é possível gerar audiência para campanhas em rascunho ou agendadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audience_name = request.data.get("name", "Audiência Principal")
        filter_criteria = request.data.get("filter_criteria", {})

        qs = build_audience_queryset(request.org, campaign.campaign_type, filter_criteria)
        contacts = list(qs)

        # Create audience record
        audience = CampaignAudience.objects.create(
            org=request.org,
            campaign=campaign,
            name=audience_name,
            filter_criteria=filter_criteria,
            contact_count=len(contacts),
        )

        # Create recipients (skip duplicates via unique_together)
        created = 0
        for contact in contacts:
            _, was_created = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                contact=contact,
                defaults={"org": request.org, "status": "pending"},
            )
            if was_created:
                created += 1

        # Update campaign total
        campaign.total_recipients = campaign.recipients.count()
        campaign.save(update_fields=["total_recipients"])

        return Response({
            "audience_id": str(audience.id),
            "contacts_matched": len(contacts),
            "recipients_created": created,
            "total_recipients": campaign.total_recipients,
        }, status=status.HTTP_201_CREATED)


class CampaignRecipientListView(APIView):
    """Listar recipients de uma campanha com paginação."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request, campaign_id):
        if not Campaign.objects.for_org(request.org).filter(pk=campaign_id).exists():
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = CampaignRecipient.objects.filter(
            campaign_id=campaign_id, org=request.org
        ).select_related("contact").order_by("-created_at")

        # Filter by status
        recipient_status = request.query_params.get("status")
        if recipient_status:
            qs = qs.filter(status=recipient_status)

        # Pagination
        limit = min(int(request.query_params.get("limit", 50)), 200)
        offset = int(request.query_params.get("offset", 0))
        total = qs.count()

        serializer = CampaignRecipientSerializer(qs[offset:offset + limit], many=True)
        return Response({
            "results": serializer.data,
            "total": total,
            "limit": limit,
            "offset": offset,
        })


class CampaignStepListCreateView(APIView):
    """Listar e criar steps de uma campanha nurture_sequence."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def _get_campaign(self, request, campaign_id):
        try:
            return Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return None

    def get(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = CampaignStep.objects.filter(campaign=campaign, org=request.org)
        serializer = CampaignStepSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if campaign.campaign_type != "nurture_sequence":
            return Response(
                {"error": "Steps só podem ser adicionados a campanhas do tipo nurture_sequence."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CampaignStepWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.org, campaign=campaign)
        return Response(
            CampaignStepSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


class CampaignStepDetailView(APIView):
    """Detalhe, atualização e exclusão de step."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def _get_step(self, request, campaign_id, step_id):
        try:
            return CampaignStep.objects.filter(
                campaign_id=campaign_id, org=request.org
            ).get(pk=step_id)
        except CampaignStep.DoesNotExist:
            return None

    def get(self, request, campaign_id, step_id):
        step = self._get_step(request, campaign_id, step_id)
        if not step:
            return Response(
                {"error": "Etapa não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CampaignStepSerializer(step).data)

    def patch(self, request, campaign_id, step_id):
        step = self._get_step(request, campaign_id, step_id)
        if not step:
            return Response(
                {"error": "Etapa não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CampaignStepWriteSerializer(step, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CampaignStepSerializer(serializer.instance).data)

    def delete(self, request, campaign_id, step_id):
        step = self._get_step(request, campaign_id, step_id)
        if not step:
            return Response(
                {"error": "Etapa não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        step.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampaignAnalyticsView(APIView):
    """Analytics de uma campanha: taxas de entrega, abertura, clique."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request, campaign_id):
        try:
            campaign = Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sent = campaign.sent_count
        delivered = campaign.delivered_count
        opened = campaign.opened_count
        clicked = campaign.clicked_count

        # Safe division
        delivery_rate = round((delivered / sent * 100), 2) if sent > 0 else 0
        open_rate = round((opened / delivered * 100), 2) if delivered > 0 else 0
        click_rate = round((clicked / opened * 100), 2) if opened > 0 else 0

        # Count unsubscribed
        unsubscribed_count = CampaignRecipient.objects.filter(
            campaign=campaign, org=request.org, status="unsubscribed"
        ).count()

        return Response({
            "campaign_id": str(campaign.id),
            "name": campaign.name,
            "campaign_type": campaign.campaign_type,
            "status": campaign.status,
            "total_recipients": campaign.total_recipients,
            "sent_count": sent,
            "delivered_count": delivered,
            "opened_count": opened,
            "clicked_count": clicked,
            "failed_count": campaign.failed_count,
            "bounce_count": campaign.bounce_count,
            "unsubscribed_count": unsubscribed_count,
            "delivery_rate": delivery_rate,
            "open_rate": open_rate,
            "click_rate": click_rate,
        })


class CampaignScheduleView(APIView):
    """Agendar campanha para envio."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, campaign_id):
        try:
            campaign = Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if campaign.status not in ("draft",):
            return Response(
                {"error": "Só é possível agendar campanhas em rascunho."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if campaign.total_recipients == 0:
            return Response(
                {"error": "Campanha não possui destinatários. Gere a audiência primeiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scheduled_at = request.data.get("scheduled_at")
        if not scheduled_at:
            return Response(
                {"error": "Data de agendamento é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.scheduled_at = scheduled_at
        campaign.status = "scheduled"
        campaign.save(update_fields=["scheduled_at", "status", "updated_at"])

        return Response(CampaignSerializer(campaign).data)


class CampaignPauseResumeView(APIView):
    """Pausar ou retomar campanha em execução."""

    permission_classes = [IsAuthenticated, HasOrgContext]

    def post(self, request, campaign_id):
        try:
            campaign = Campaign.objects.for_org(request.org).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {"error": "Campanha não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = request.data.get("action")

        if action == "pause" and campaign.status == "running":
            campaign.status = "paused"
            campaign.save(update_fields=["status", "updated_at"])

            # Cancel all pending ScheduledJobs for this campaign
            from campaigns.job_generator import cancel_campaign_jobs
            cancelled = cancel_campaign_jobs(campaign)

            data = CampaignSerializer(campaign).data
            data["jobs_cancelled"] = cancelled
            return Response(data)

        if action == "resume" and campaign.status == "paused":
            campaign.status = "running"
            campaign.save(update_fields=["status", "updated_at"])

            # Recreate ScheduledJobs for pending recipients
            from campaigns.job_generator import recreate_campaign_jobs
            created = recreate_campaign_jobs(campaign)

            data = CampaignSerializer(campaign).data
            data["jobs_created"] = created
            return Response(data)

        return Response(
            {"error": f"Ação '{action}' inválida para status '{campaign.status}'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
