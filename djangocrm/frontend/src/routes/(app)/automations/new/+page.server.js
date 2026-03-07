/**
 * New Automation Page
 *
 * Django endpoint: POST /api/automations/
 */

import { error, fail, redirect } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals }) {
  if (!locals.org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }
  return {};
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get('name')?.toString().trim();
    const automationType = formData.get('automation_type')?.toString();
    const configJsonRaw = formData.get('config_json')?.toString();

    if (!name) {
      return fail(400, { error: 'Nome é obrigatório.' });
    }
    if (!automationType) {
      return fail(400, { error: 'Tipo de automação é obrigatório.' });
    }

    let configJson = {};
    if (configJsonRaw) {
      try {
        configJson = JSON.parse(configJsonRaw);
      } catch {
        return fail(400, { error: 'Configuração JSON inválida.' });
      }
    }

    try {
      const result = await apiRequest('/automations/', {
        method: 'POST',
        body: {
          name,
          automation_type: automationType,
          config_json: configJson,
          is_active: false
        }
      }, cookies);

      throw redirect(303, '/automations');
    } catch (err) {
      if (err?.status === 303) throw err;
      const message = err?.body?.config_json || err?.body?.detail || 'Erro ao criar automação.';
      return fail(400, { error: typeof message === 'string' ? message : JSON.stringify(message) });
    }
  }
};
