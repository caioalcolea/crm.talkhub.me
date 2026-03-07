/**
 * Automations List Page
 *
 * Django endpoint: GET /api/automations/
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
  const isActive = url.searchParams.get('is_active') || '';

  try {
    let endpoint = '/automations/';
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (isActive) params.append('is_active', isActive);
    const qs = params.toString();
    if (qs) endpoint += `?${qs}`;

    const automations = await apiRequest(endpoint, {}, cookies);

    return {
      automations: automations || [],
      filters: { type, is_active: isActive }
    };
  } catch (err) {
    console.error('Failed to load automations:', err);
    return { automations: [], filters: { type, is_active: isActive } };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  toggleActive: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');
    const isActive = formData.get('is_active') === 'true';

    try {
      await apiRequest(`/automations/${id}/`, {
        method: 'PATCH',
        body: { is_active: !isActive }
      }, cookies);
      return { success: true, toast: isActive ? 'Automação desativada.' : 'Automação ativada.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao alterar status da automação.' });
    }
  },

  delete: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');

    try {
      await apiRequest(`/automations/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Automação excluída.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao excluir automação.' });
    }
  }
};
