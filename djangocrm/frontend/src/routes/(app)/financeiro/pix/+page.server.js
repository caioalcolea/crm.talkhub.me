import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const filters = {
    status: url.searchParams.get('status') || '',
    transaction_type: url.searchParams.get('transaction_type') || '',
    date_from: url.searchParams.get('date_from') || '',
    date_to: url.searchParams.get('date_to') || '',
    search: url.searchParams.get('search') || ''
  };

  try {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.transaction_type) params.append('transaction_type', filters.transaction_type);
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.search) params.append('search', filters.search);

    const qs = params.toString();
    const response = await apiRequest(
      `/financeiro/pix/transactions/${qs ? `?${qs}` : ''}`,
      {},
      { cookies, org }
    );

    let transactions = [];
    if (response.results) {
      transactions = response.results;
    } else if (Array.isArray(response)) {
      transactions = response;
    }

    return { transactions, filters };
  } catch (err) {
    console.error('PIX transactions load error:', err);
    return { transactions: [], filters };
  }
}
