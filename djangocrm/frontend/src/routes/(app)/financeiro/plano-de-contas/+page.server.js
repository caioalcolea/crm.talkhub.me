import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  try {
    const grupos = await apiRequest(
      '/financeiro/plano-de-contas/grupos/?tree=true',
      {},
      { cookies, org }
    );

    return { grupos: Array.isArray(grupos) ? grupos : grupos.results || [] };
  } catch (err) {
    console.error('Plano de Contas load error:', err);
    return { grupos: [] };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  createGrupo: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const body = {
      codigo: form.get('codigo'),
      nome: form.get('nome'),
      descricao: form.get('descricao') || '',
      ordem: parseInt(form.get('ordem') || '0'),
      color: form.get('color') || '#6B7280',
      applies_to: form.get('applies_to') || 'AMBOS'
    };

    try {
      await apiRequest('/financeiro/plano-de-contas/grupos/', { method: 'POST', body }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  editGrupo: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const id = form.get('id');
    const body = {
      codigo: form.get('codigo'),
      nome: form.get('nome'),
      descricao: form.get('descricao') || '',
      ordem: parseInt(form.get('ordem') || '0'),
      color: form.get('color') || '#6B7280',
      applies_to: form.get('applies_to') || 'AMBOS'
    };

    try {
      await apiRequest(`/financeiro/plano-de-contas/grupos/${id}/`, { method: 'PATCH', body }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  archiveGrupo: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });
    const form = await request.formData();
    const id = form.get('id');
    try {
      await apiRequest(`/financeiro/plano-de-contas/grupos/${id}/`, { method: 'PATCH', body: { is_active: false } }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  restoreGrupo: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });
    const form = await request.formData();
    const id = form.get('id');
    try {
      await apiRequest(`/financeiro/plano-de-contas/grupos/${id}/`, { method: 'PATCH', body: { is_active: true } }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  createConta: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const body = {
      grupo: form.get('grupo'),
      nome: form.get('nome'),
      descricao: form.get('descricao') || ''
    };

    try {
      await apiRequest('/financeiro/plano-de-contas/', { method: 'POST', body }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  editConta: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const id = form.get('id');
    const body = {
      nome: form.get('nome'),
      descricao: form.get('descricao') || ''
    };

    try {
      await apiRequest(`/financeiro/plano-de-contas/${id}/`, { method: 'PATCH', body }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  archiveConta: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });
    const form = await request.formData();
    const id = form.get('id');
    try {
      await apiRequest(`/financeiro/plano-de-contas/${id}/`, { method: 'PATCH', body: { is_active: false } }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  deleteGrupo: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });
    const form = await request.formData();
    const id = form.get('id');
    try {
      await apiRequest(`/financeiro/plano-de-contas/grupos/${id}/`, { method: 'DELETE' }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  deleteConta: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });
    const form = await request.formData();
    const id = form.get('id');
    try {
      await apiRequest(`/financeiro/plano-de-contas/${id}/`, { method: 'DELETE' }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  }
};
