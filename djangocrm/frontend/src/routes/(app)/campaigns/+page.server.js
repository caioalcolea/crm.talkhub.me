/**
 * Campaigns List Page
 *
 * Django endpoint: GET /api/campaigns/
 */

import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, url }) {
  const org = locals.org;
  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  const type = url.searchParams.get('type') || '';
  const status = url.searchParams.get('status') || '';

  try {
    let endpoint = '/campaigns/';
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (status) params.append('status', status);
    const qs = params.toString();
    if (qs) endpoint += `?${qs}`;

    const campaigns = await apiRequest(endpoint, {}, cookies);

    return {
      campaigns: campaigns || [],
      filters: { type, status }
    };
  } catch (err) {
    console.error('Failed to load campaigns:', err);
    return { campaigns: [], filters: { type, status } };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  delete: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');

    try {
      await apiRequest(`/campaigns/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Campanha excluída.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao excluir campanha.' });
    }
  },

  pauseResume: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    const action = formData.get('action');

    try {
      await apiRequest(`/campaigns/${id}/pause-resume/`, {
        method: 'POST',
        body: { action }
      }, cookies);
      const msg = action === 'pause' ? 'Campanha pausada.' : 'Campanha retomada.';
      return { success: true, toast: msg };
    } catch (err) {
      return fail(400, { error: 'Erro ao alterar status da campanha.' });
    }
  }
};
