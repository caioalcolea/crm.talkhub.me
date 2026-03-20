import { error, fail } from '@sveltejs/kit';
import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const filters = {
    search: url.searchParams.get('search') || '',
    tipo: url.searchParams.get('tipo') || '',
    status: url.searchParams.get('status') || '',
    plano_de_contas: url.searchParams.get('plano_de_contas') || '',
    date_from: url.searchParams.get('date_from') || '',
    date_to: url.searchParams.get('date_to') || ''
  };

  try {
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '20');

    const queryParams = buildQueryParams({ page, limit, sort: 'data_primeiro_vencimento', order: 'desc' });
    if (filters.search) queryParams.append('search', filters.search);
    if (filters.tipo) queryParams.append('tipo', filters.tipo);
    if (filters.status) queryParams.append('status', filters.status);
    if (filters.plano_de_contas) queryParams.append('plano_de_contas', filters.plano_de_contas);
    if (filters.date_from) queryParams.append('date_from', filters.date_from);
    if (filters.date_to) queryParams.append('date_to', filters.date_to);

    const [lancamentosRes, formOptions] = await Promise.all([
      apiRequest(`/financeiro/lancamentos/?${queryParams.toString()}`, {}, { cookies, org }),
      apiRequest('/financeiro/form-options/', {}, { cookies, org })
    ]);

    let lancamentos = [];
    let totalCount = 0;
    if (lancamentosRes.results) {
      lancamentos = lancamentosRes.results;
      totalCount = lancamentosRes.count || 0;
    } else if (Array.isArray(lancamentosRes)) {
      lancamentos = lancamentosRes;
      totalCount = lancamentos.length;
    }

    return {
      lancamentos,
      formOptions,
      pagination: { page, limit, total: totalCount, totalPages: Math.ceil(totalCount / limit) },
      filters
    };
  } catch (err) {
    console.error('Lancamentos load error:', err);
    return {
      lancamentos: [],
      formOptions: { planos: [], formas_pagamento: [], accounts: [], contacts: [], opportunities: [], currencies: [] },
      pagination: { page: 1, limit: 20, total: 0, totalPages: 0 },
      filters
    };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, locals, cookies }) => {
    const org = locals.org;
    if (!org) return fail(401, { error: 'Contexto de organização é obrigatório' });

    const form = await request.formData();
    const body = {
      tipo: form.get('tipo'),
      descricao: form.get('descricao'),
      observacoes: form.get('observacoes') || '',
      plano_de_contas: form.get('plano_de_contas') || null,
      account: form.get('account') || null,
      contact: form.get('contact') || null,
      opportunity: form.get('opportunity') || null,
      invoice: form.get('invoice') || null,
      product: form.get('product') || null,
      quantity: parseFloat(form.get('quantity') || '1'),
      currency: form.get('currency') || 'BRL',
      valor_total: form.get('valor_total'),
      exchange_rate_to_base: form.get('exchange_rate_to_base') || '1',
      exchange_rate_type: form.get('exchange_rate_type') || 'FIXO',
      forma_pagamento: form.get('forma_pagamento') || null,
      numero_parcelas: parseInt(form.get('numero_parcelas') || '1'),
      data_primeiro_vencimento: form.get('data_primeiro_vencimento'),
      is_recorrente: form.get('is_recorrente') === 'true',
      recorrencia_tipo: form.get('recorrencia_tipo') || '',
      data_fim_recorrencia: form.get('data_fim_recorrencia') || null
    };

    try {
      await apiRequest('/financeiro/lancamentos/', { method: 'POST', body }, { cookies, org });
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
      await apiRequest(`/financeiro/lancamentos/${id}/`, { method: 'DELETE' }, { cookies, org });
      return { success: true };
    } catch (err) {
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  }
};
