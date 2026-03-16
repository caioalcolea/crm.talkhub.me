from django.urls import path

from opportunity.views.aging_views import StageAgingConfigView
from opportunity.views.breakdown_views import (
    GoalBreakdownDetailView,
    GoalBreakdownListView,
)
from opportunity.views.goal_views import (
    SalesGoalDashboardView,
    SalesGoalDetailView,
    SalesGoalLeaderboardView,
    SalesGoalListView,
)
from opportunity.views.line_item_views import (
    OpportunityLineItemDetailView,
    OpportunityLineItemListView,
)
from opportunity.views.opportunity_interactions import (
    OpportunityAttachmentView,
    OpportunityCommentView,
)
from opportunity.views.kanban_views import (
    OpportunityKanbanView,
    OpportunityMoveView,
    OpportunityPipelineDetailView,
    OpportunityPipelineListCreateView,
    OpportunityStageCreateView,
    OpportunityStageDetailView,
    OpportunityStageReorderView,
)
from opportunity.views.opportunity_views import (
    OpportunityDetailView,
    OpportunityListView,
    OpportunityRelatedView,
)

app_name = "api_opportunities"

urlpatterns = [
    path("", OpportunityListView.as_view()),
    # Kanban
    path("kanban/", OpportunityKanbanView.as_view(), name="opportunity-kanban"),
    # Pipelines
    path("pipelines/", OpportunityPipelineListCreateView.as_view(), name="opportunity-pipelines"),
    path("pipelines/<str:pk>/", OpportunityPipelineDetailView.as_view(), name="opportunity-pipeline-detail"),
    path("pipelines/<str:pipeline_pk>/stages/", OpportunityStageCreateView.as_view(), name="opportunity-stage-create"),
    path("pipelines/<str:pipeline_pk>/stages/reorder/", OpportunityStageReorderView.as_view(), name="opportunity-stage-reorder"),
    path("stages/<str:pk>/", OpportunityStageDetailView.as_view(), name="opportunity-stage-detail"),
    path("aging-config/", StageAgingConfigView.as_view()),
    path("goals/", SalesGoalListView.as_view()),
    path("goals/dashboard/", SalesGoalDashboardView.as_view()),
    path("goals/leaderboard/", SalesGoalLeaderboardView.as_view()),
    path("goals/<str:pk>/", SalesGoalDetailView.as_view()),
    # Goal Breakdowns
    path(
        "goals/<str:goal_id>/breakdowns/",
        GoalBreakdownListView.as_view(),
        name="goal-breakdowns-list",
    ),
    path(
        "goals/<str:goal_id>/breakdowns/<str:pk>/",
        GoalBreakdownDetailView.as_view(),
        name="goal-breakdowns-detail",
    ),
    path("<str:pk>/move/", OpportunityMoveView.as_view(), name="opportunity-move"),
    path("<str:pk>/related/", OpportunityRelatedView.as_view(), name="opportunity-related"),
    path("<str:pk>/", OpportunityDetailView.as_view()),
    path("comment/<str:pk>/", OpportunityCommentView.as_view()),
    path("attachment/<str:pk>/", OpportunityAttachmentView.as_view()),
    # Line items
    path(
        "<str:opportunity_id>/line-items/",
        OpportunityLineItemListView.as_view(),
        name="opportunity-line-items-list",
    ),
    path(
        "<str:opportunity_id>/line-items/<str:line_item_id>/",
        OpportunityLineItemDetailView.as_view(),
        name="opportunity-line-items-detail",
    ),
]
