/**
 * Campaign Detail / Configure Page
 *
 * Django endpoints:
 *   GET /api/campaigns/<id>/
 *   POST /api/campaigns/<id>/audience/preview/
 *   POST /api/campaigns/<id>/audience/generate/
 *   POST /api/campaigns/<id>/schedule/
 *   POST /api/campaigns/<id>/pause-resume/
 */

import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, params }) {
  const org = locals.org;
  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  const { id } = params;

  try {
    const campaign = await apiRequest(`/campaigns/${id}/`, {}, cookies);
    return { campaign };
  } catch (err) {
    console.error('Failed to load campaign:', err);
    throw error(404, 'Campanha não encontrada');
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  previewAudience: async ({ request, cookies, params }) => {
    const formData = await request.formData();
    const filterCriteriaRaw = formData.get('filter_criteria')?.toString() || '{}';

    let filterCriteria = {};
    try {
      filterCriteria = JSON.parse(filterCriteriaRaw);
    } catch {
      return fail(400, { error: 'Critérios de filtro inválidos.' });
    }

    try {
      const result = await apiRequest(`/campaigns/${params.id}/audience/preview/`, {
        method: 'POST',
        body: { filter_criteria: filterCriteria }
      }, cookies);
      return { previewCount: result.count, filterCriteria };
    } catch (err) {
      return fail(400, { error: 'Erro ao calcular preview da audiência.' });
    }
  },

  generateAudience: async ({ request, cookies, params }) => {
    const formData = await request.formData();
    const filterCriteriaRaw = formData.get('filter_criteria')?.toString() || '{}';
    const audienceName = formData.get('audience_name')?.toString() || 'Audiência Principal';

    let filterCriteria = {};
    try {
      filterCriteria = JSON.parse(filterCriteriaRaw);
    } catch {
      return fail(400, { error: 'Critérios de filtro inválidos.' });
    }

    try {
      const result = await apiRequest(`/campaigns/${params.id}/audience/generate/`, {
        method: 'POST',
        body: { filter_criteria: filterCriteria, name: audienceName }
      }, cookies);
      return {
        toast: `Audiência gerada: ${result.recipients_created} destinatários criados.`,
        totalRecipients: result.total_recipients
      };
    } catch (err) {
      const msg = err?.message || 'Erro ao gerar audiência.';
      return fail(400, { error: msg });
    }
  },

  schedule: async ({ request, cookies, params }) => {
    const formData = await request.formData();
    const scheduledAt = formData.get('scheduled_at')?.toString();

    if (!scheduledAt) {
      return fail(400, { error: 'Data de agendamento é obrigatória.' });
    }

    try {
      await apiRequest(`/campaigns/${params.id}/schedule/`, {
        method: 'POST',
        body: { scheduled_at: scheduledAt }
      }, cookies);
      return { toast: 'Campanha agendada com sucesso.' };
    } catch (err) {
      const msg = err?.message || 'Erro ao agendar campanha.';
      return fail(400, { error: msg });
    }
  },

  pauseResume: async ({ request, cookies, params }) => {
    const formData = await request.formData();
    const action = formData.get('action')?.toString();

    try {
      await apiRequest(`/campaigns/${params.id}/pause-resume/`, {
        method: 'POST',
        body: { action }
      }, cookies);
      const msg = action === 'pause' ? 'Campanha pausada.' : 'Campanha retomada.';
      return { toast: msg };
    } catch (err) {
      return fail(400, { error: 'Erro ao alterar status da campanha.' });
    }
  }
};
