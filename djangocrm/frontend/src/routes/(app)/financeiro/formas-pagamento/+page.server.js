import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  try {
    const res = await apiRequest('/financeiro/formas-pagamento/', {}, { cookies, org });
    const formas = Array.isArray(res) ? res : res.results || [];
    return { formas };
  } catch (err) {
    console.error('Formas de Pagamento load error:', err);
    return { formas: [] };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const body = { nome: form.get('nome') };

    try {
      await apiRequest('/financeiro/formas-pagamento/', { method: 'POST', body }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  toggle: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const id = form.get('id');
    const isActive = form.get('is_active') === 'true';

    try {
      await apiRequest(
        `/financeiro/formas-pagamento/${id}/`,
        { method: 'PATCH', body: { is_active: !isActive } },
        { cookies, org }
      );
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  delete: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const id = form.get('id');

    try {
      await apiRequest(`/financeiro/formas-pagamento/${id}/`, { method: 'DELETE' }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  }
};
