/**
 * Goals Dashboard Page - Server
 *
 * Django endpoint: GET /api/opportunities/goals/dashboard/
 */

import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

export async function load({ locals, cookies, url }) {
  const userId = locals.user?.id;
  const org = locals.org;

  if (!userId) {
    return {
      goals: [],
      summary: { total_goals: 0, on_track: 0, at_risk: 0, behind: 0, completed: 0 },
      options: { teams: [] }
    };
  }

  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  const periodType = url.searchParams.get('period_type') || '';
  const teamId = url.searchParams.get('team') || '';

  try {
    const params = new URLSearchParams();
    if (periodType) params.append('period_type', periodType);
    if (teamId) params.append('team', teamId);
    const qs = params.toString();

    const [dashboardResponse, teamsResponse] = await Promise.all([
      apiRequest(
        `/opportunities/goals/dashboard/${qs ? `?${qs}` : ''}`,
        {},
        { cookies, org }
      ),
      apiRequest('/users/get-teams-and-users/', {}, { cookies, org }).catch(() => ({
        teams: [],
        profiles: []
      }))
    ]);

    const goals = (dashboardResponse.goals || []).map((goal) => ({
      id: goal.id,
      name: goal.name,
      goalType: goal.goal_type,
      targetValue: goal.target_value ? Number(goal.target_value) : 0,
      periodType: goal.period_type,
      periodStart: goal.period_start,
      periodEnd: goal.period_end,
      assignedTo: goal.assigned_to_detail
        ? {
            id: goal.assigned_to_detail.id,
            name: goal.assigned_to_detail.user_details?.email || goal.assigned_to_detail.email
          }
        : null,
      team: goal.team_detail ? { id: goal.team_detail.id, name: goal.team_detail.name } : null,
      isActive: goal.is_active,
      progressValue: goal.progress_value || 0,
      progressPercent: goal.progress_percent || 0,
      status: goal.status || 'behind',
      daysRemaining: goal.days_remaining ?? 0,
      breakdowns: (goal.breakdowns || []).map((bd) => ({
        id: bd.id,
        breakdownType: bd.breakdown_type,
        breakdownKey: bd.breakdown_key,
        breakdownLabel: bd.breakdown_label,
        targetValue: Number(bd.target_value) || 0,
        currentValue: Number(bd.current_value) || 0,
        progressPercent: bd.progress_percent || 0,
        status: bd.status || 'behind'
      }))
    }));

    const teams = (teamsResponse.teams || []).map((t) => ({
      id: t.id,
      name: t.name
    }));

    return {
      goals,
      summary: dashboardResponse.summary || {
        total_goals: 0,
        on_track: 0,
        at_risk: 0,
        behind: 0,
        completed: 0
      },
      options: { teams },
      filters: { periodType, teamId }
    };
  } catch (err) {
    console.error('Error loading goals dashboard:', err);
    throw error(500, 'Falha ao carregar dashboard de metas');
  }
}
