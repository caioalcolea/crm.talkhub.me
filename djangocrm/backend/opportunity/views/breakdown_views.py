"""
Views for GoalBreakdown CRUD — desdobramento de metas.

Endpoints:
    GET    /api/opportunities/goals/<goal_id>/breakdowns/
    POST   /api/opportunities/goals/<goal_id>/breakdowns/
    GET    /api/opportunities/goals/<goal_id>/breakdowns/<pk>/
    PUT    /api/opportunities/goals/<goal_id>/breakdowns/<pk>/
    DELETE /api/opportunities/goals/<goal_id>/breakdowns/<pk>/
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext
from opportunity.models import GoalBreakdown, SalesGoal
from opportunity.serializers import (
    GoalBreakdownCreateSerializer,
    GoalBreakdownSerializer,
)


class GoalBreakdownListView(APIView):
    """List and create breakdowns for a specific goal."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def _get_goal(self, goal_id, request):
        return SalesGoal.objects.filter(
            id=goal_id, org=request.profile.org
        ).first()

    def get(self, request, goal_id, *args, **kwargs):
        goal = self._get_goal(goal_id, request)
        if not goal:
            return Response(
                {"error": True, "errors": "Meta não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        breakdowns = GoalBreakdown.objects.filter(
            goal=goal, org=request.profile.org
        ).select_related("goal")

        breakdown_type = request.query_params.get("breakdown_type")
        if breakdown_type:
            breakdowns = breakdowns.filter(breakdown_type=breakdown_type)

        serializer = GoalBreakdownSerializer(breakdowns, many=True)
        return Response(
            {
                "breakdowns": serializer.data,
                "goal_id": str(goal.id),
                "goal_target": float(goal.target_value),
            }
        )

    def post(self, request, goal_id, *args, **kwargs):
        if request.profile.role != "ADMIN" and not request.user.is_superuser:
            return Response(
                {"error": True, "errors": "Apenas administradores podem criar desdobramentos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        goal = self._get_goal(goal_id, request)
        if not goal:
            return Response(
                {"error": True, "errors": "Meta não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GoalBreakdownCreateSerializer(
            data=request.data, context={"goal": goal}
        )
        if serializer.is_valid():
            serializer.save(
                goal=goal,
                org=request.profile.org,
                created_by=request.profile.user,
            )
            return Response(
                {"error": False, "message": "Desdobramento criado com sucesso."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class GoalBreakdownDetailView(APIView):
    """Retrieve, update, delete a specific breakdown."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def _get_object(self, goal_id, pk, request):
        return GoalBreakdown.objects.filter(
            id=pk, goal_id=goal_id, org=request.profile.org
        ).select_related("goal").first()

    def get(self, request, goal_id, pk, *args, **kwargs):
        breakdown = self._get_object(goal_id, pk, request)
        if not breakdown:
            return Response(
                {"error": True, "errors": "Desdobramento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GoalBreakdownSerializer(breakdown)
        return Response(serializer.data)

    def put(self, request, goal_id, pk, *args, **kwargs):
        if request.profile.role != "ADMIN" and not request.user.is_superuser:
            return Response(
                {"error": True, "errors": "Apenas administradores podem editar desdobramentos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        breakdown = self._get_object(goal_id, pk, request)
        if not breakdown:
            return Response(
                {"error": True, "errors": "Desdobramento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GoalBreakdownCreateSerializer(
            breakdown,
            data=request.data,
            partial=True,
            context={"goal": breakdown.goal},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"error": False, "message": "Desdobramento atualizado com sucesso."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": True, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, goal_id, pk, *args, **kwargs):
        if request.profile.role != "ADMIN" and not request.user.is_superuser:
            return Response(
                {"error": True, "errors": "Apenas administradores podem excluir desdobramentos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        breakdown = self._get_object(goal_id, pk, request)
        if not breakdown:
            return Response(
                {"error": True, "errors": "Desdobramento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        breakdown.delete()
        return Response(
            {"error": False, "message": "Desdobramento excluído com sucesso."},
            status=status.HTTP_200_OK,
        )
