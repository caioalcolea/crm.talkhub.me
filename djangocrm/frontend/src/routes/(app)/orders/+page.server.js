/**
 * Purchase Orders Page
 *
 * Lists purchase orders with filters and CRUD.
 * Django endpoint: GET /api/orders/?order_type=purchase
 */

import { error, fail } from '@sveltejs/kit';
import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;

  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  const filters = {
    search: url.searchParams.get('search') || '',
    status: url.searchParams.get('status') || '',
  };

  try {
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '10');

    const queryParams = buildQueryParams({ page, limit });
    queryParams.append('order_type', 'purchase');

    if (filters.search) queryParams.append('search', filters.search);
    if (filters.status) queryParams.append('status', filters.status);

    const ordersResponse = await apiRequest(
      `/orders/?${queryParams.toString()}`,
      {},
      { cookies, org }
    );

    let orders = [];
    let totalCount = 0;

    if (ordersResponse.results) {
      orders = ordersResponse.results;
      totalCount = ordersResponse.count || 0;
    } else if (Array.isArray(ordersResponse)) {
      orders = ordersResponse;
      totalCount = orders.length;
    }

    // Also fetch products for the create form
    let products = [];
    try {
      const productsRes = await apiRequest('/invoices/products/?limit=100', {}, { cookies, org });
      products = productsRes.results || productsRes || [];
    } catch { /* non-critical */ }

    // Also fetch accounts
    let accounts = [];
    try {
      const accountsRes = await apiRequest('/accounts/?limit=100', {}, { cookies, org });
      accounts = (accountsRes.results || accountsRes || []).map(a => ({
        value: a.id,
        label: a.name
      }));
    } catch { /* non-critical */ }

    return {
      orders,
      pagination: {
        page,
        limit,
        total: totalCount,
        totalPages: Math.ceil(totalCount / limit) || 1
      },
      filters,
      products,
      accounts,
    };
  } catch (err) {
    console.error('Error loading orders:', err);
    throw error(500, `Falha ao carregar pedidos: ${err.message}`);
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, locals, cookies }) => {
    try {
      const form = await request.formData();

      const orderData = {
        name: form.get('name')?.toString().trim() || '',
        order_type: 'purchase',
        status: 'DRAFT',
        account: form.get('account')?.toString() || null,
        currency: form.get('currency')?.toString() || 'BRL',
        order_date: form.get('order_date')?.toString() || null,
        total_amount: form.get('total_amount')?.toString() || '0',
        description: form.get('description')?.toString() || '',
      };

      if (!orderData.account) delete orderData.account;

      await apiRequest(
        '/orders/',
        { method: 'POST', body: orderData },
        { cookies, org: locals.org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error creating order:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  activate: async ({ request, locals, cookies }) => {
    try {
      const form = await request.formData();
      const orderId = form.get('orderId')?.toString();

      if (!orderId) return fail(400, { error: 'ID do pedido é obrigatório' });

      await apiRequest(
        `/orders/${orderId}/activate/`,
        { method: 'POST' },
        { cookies, org: locals.org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error activating order:', err);
      return fail(400, { error: err.message || 'Falha ao ativar pedido' });
    }
  },

  delete: async ({ request, locals, cookies }) => {
    try {
      const form = await request.formData();
      const orderId = form.get('orderId')?.toString();

      if (!orderId) return fail(400, { error: 'ID do pedido é obrigatório' });

      await apiRequest(
        `/orders/${orderId}/`,
        { method: 'DELETE' },
        { cookies, org: locals.org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error deleting order:', err);
      return fail(400, { error: err.message || 'Falha ao excluir pedido' });
    }
  }
};
