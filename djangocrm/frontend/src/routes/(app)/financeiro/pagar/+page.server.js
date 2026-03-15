import { error } from '@sveltejs/kit';
import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const filters = {
    search: url.searchParams.get('search') || '',
    status: url.searchParams.get('status') || '',
    vencimento_from: url.searchParams.get('vencimento_from') || '',
    vencimento_to: url.searchParams.get('vencimento_to') || ''
  };

  try {
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '100');

    const queryParams = buildQueryParams({ page, limit, sort: 'data_vencimento', order: 'asc' });
    queryParams.append('tipo', 'PAGAR');
    if (filters.search) queryParams.append('search', filters.search);
    if (filters.status) queryParams.append('status', filters.status);
    if (filters.vencimento_from) queryParams.append('vencimento_from', filters.vencimento_from);
    if (filters.vencimento_to) queryParams.append('vencimento_to', filters.vencimento_to);

    const [res, activeReminders] = await Promise.all([
      apiRequest(`/financeiro/parcelas/?${queryParams.toString()}`, {}, { cookies, org }),
      apiRequest('/assistant/reminder-policies/?module_key=financeiro&is_active=true', {}, { cookies, org }).catch(() => []),
    ]);

    let parcelas = [];
    let totalCount = 0;
    if (res.results) {
      parcelas = res.results;
      totalCount = res.count || 0;
    } else if (Array.isArray(res)) {
      parcelas = res;
      totalCount = parcelas.length;
    }

    // Extract lancamento IDs that have active reminder policies
    const reminderLancamentoIds = (Array.isArray(activeReminders) ? activeReminders : activeReminders?.results || [])
      .map(r => r.target_object_id)
      .filter(Boolean);

    return {
      parcelas,
      pagination: { page, limit, total: totalCount, totalPages: Math.ceil(totalCount / limit) },
      filters,
      reminderLancamentoIds,
    };
  } catch (err) {
    console.error('Pagar load error:', err);
    return { parcelas: [], pagination: { page: 1, limit: 25, total: 0, totalPages: 0 }, filters };
  }
}
