/**
 * Invoice Reports Dashboard
 *
 * Displays invoice summaries, revenue reports, and aging analysis.
 */

import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;

  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  try {
    // Get date range from URL params or defaults
    const today = new Date();
    const yearAgo = new Date(today);
    yearAgo.setFullYear(yearAgo.getFullYear() - 1);

    const startDate = url.searchParams.get('start_date') || yearAgo.toISOString().split('T')[0];
    const endDate = url.searchParams.get('end_date') || today.toISOString().split('T')[0];
    const groupBy = url.searchParams.get('group_by') || 'month';

    // Fetch all reports in parallel (including product reports)
    const [dashboardRes, revenueRes, agingRes, marginRes, inventoryRes, topRes] = await Promise.all([
      apiRequest('/invoices/reports/dashboard/', {}, { cookies, org }),
      apiRequest(
        `/invoices/reports/revenue/?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`,
        {},
        { cookies, org }
      ),
      apiRequest('/invoices/reports/aging/', {}, { cookies, org }),
      apiRequest('/invoices/reports/product-margin/', {}, { cookies, org }).catch(() => ({ results: [] })),
      apiRequest('/invoices/reports/inventory-summary/', {}, { cookies, org }).catch(() => ({ results: [], summary: {} })),
      apiRequest('/invoices/reports/top-products/?limit=10', {}, { cookies, org }).catch(() => ({ results: [] })),
    ]);

    return {
      dashboard: dashboardRes,
      revenue: revenueRes,
      aging: agingRes,
      productMargin: marginRes,
      inventory: inventoryRes,
      topProducts: topRes,
      filters: {
        startDate,
        endDate,
        groupBy
      }
    };
  } catch (err) {
    console.error('Error loading reports:', err);
    throw error(500, `Falha ao carregar relatórios: ${err.message}`);
  }
}
