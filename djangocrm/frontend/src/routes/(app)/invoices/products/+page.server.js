/**
 * Products/Services List Page
 *
 * Product and service catalog with inventory, cost, and tax management.
 * Django endpoint: GET /api/invoices/products/
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
    category: url.searchParams.get('category') || '',
    is_active: url.searchParams.get('is_active') || '',
    product_type: url.searchParams.get('product_type') || ''
  };

  try {
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const sort = url.searchParams.get('sort') || '-created_at';

    const queryParams = buildQueryParams({
      page,
      limit,
      sort: sort.startsWith('-') ? sort.substring(1) : sort,
      order: sort.startsWith('-') ? 'desc' : 'asc'
    });

    if (filters.search) queryParams.append('search', filters.search);
    if (filters.category) queryParams.append('category', filters.category);
    if (filters.is_active) queryParams.append('is_active', filters.is_active);
    if (filters.product_type) queryParams.append('product_type', filters.product_type);

    const productsResponse = await apiRequest(
      `/invoices/products/?${queryParams.toString()}`,
      {},
      { cookies, org }
    );

    let products = [];
    let totalCount = 0;

    if (productsResponse.results) {
      products = productsResponse.results;
      totalCount = productsResponse.count || 0;
    } else if (Array.isArray(productsResponse)) {
      products = productsResponse;
      totalCount = products.length;
    }

    const transformedProducts = products.map((product) => ({
      id: product.id,
      name: product.name,
      description: product.description || '',
      sku: product.sku || '',
      product_type: product.product_type || 'product',
      price: product.price || '0.00',
      cost_price: product.cost_price || '0.00',
      currency: product.currency || 'BRL',
      category: product.category || '',
      isActive: product.is_active,
      default_tax_rate: product.default_tax_rate || '0.00',
      tax_profile: product.tax_profile || {},
      gateway_fee_percent: product.gateway_fee_percent || '0.00',
      gateway_fee_fixed: product.gateway_fee_fixed || '0.00',
      track_inventory: product.track_inventory || false,
      stock_quantity: product.stock_quantity || '0.00',
      stock_min_alert: product.stock_min_alert || '0.00',
      unit_of_measure: product.unit_of_measure || 'un',
      margin_percent: product.margin_percent || '0.00',
      net_price: product.net_price || '0.00',
      is_low_stock: product.is_low_stock || false,
      supplier_account: product.supplier_account || null,
      supplier_account_name: product.supplier_account_name || '',
      default_plano_receita: product.default_plano_receita || null,
      default_plano_custo: product.default_plano_custo || null,
      plano_receita_nome: product.plano_receita_nome || '',
      plano_custo_nome: product.plano_custo_nome || '',
      createdAt: product.created_at
    }));

    const categories = [...new Set(products.map((p) => p.category).filter(Boolean))].map((c) => ({
      value: c,
      label: c
    }));

    return {
      products: transformedProducts,
      pagination: {
        page,
        limit,
        total: totalCount,
        totalPages: Math.ceil(totalCount / limit) || 1
      },
      filters,
      categories
    };
  } catch (err) {
    console.error('Error loading products from API:', err);
    throw error(500, `Falha ao carregar produtos: ${err.message}`);
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, locals, cookies }) => {
    try {
      const form = await request.formData();

      const productData = {
        name: form.get('name')?.toString().trim() || '',
        description: form.get('description')?.toString() || '',
        sku: form.get('sku')?.toString() || '',
        product_type: form.get('product_type')?.toString() || 'product',
        price: form.get('price')?.toString() || '0',
        cost_price: form.get('cost_price')?.toString() || '0',
        currency: form.get('currency')?.toString() || 'BRL',
        category: form.get('category')?.toString() || '',
        is_active: form.get('isActive') === 'true',
        default_tax_rate: form.get('default_tax_rate')?.toString() || '0',
        gateway_fee_percent: form.get('gateway_fee_percent')?.toString() || '0',
        gateway_fee_fixed: form.get('gateway_fee_fixed')?.toString() || '0',
        track_inventory: form.get('track_inventory') === 'true',
        stock_quantity: form.get('stock_quantity')?.toString() || '0',
        stock_min_alert: form.get('stock_min_alert')?.toString() || '0',
        unit_of_measure: form.get('unit_of_measure')?.toString() || 'un'
      };

      await apiRequest(
        '/invoices/products/',
        { method: 'POST', body: productData },
        { cookies, org: locals.org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error creating product:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  update: async ({ request, locals, cookies }) => {
    try {
      const form = await request.formData();
      const productId = form.get('productId')?.toString();

      if (!productId) {
        return fail(400, { error: 'ID do produto é obrigatório' });
      }

      const productData = {
        name: form.get('name')?.toString().trim() || '',
        description: form.get('description')?.toString() || '',
        sku: form.get('sku')?.toString() || '',
        product_type: form.get('product_type')?.toString() || 'product',
        price: form.get('price')?.toString() || '0',
        cost_price: form.get('cost_price')?.toString() || '0',
        currency: form.get('currency')?.toString() || 'BRL',
        category: form.get('category')?.toString() || '',
        is_active: form.get('isActive') === 'true',
        default_tax_rate: form.get('default_tax_rate')?.toString() || '0',
        gateway_fee_percent: form.get('gateway_fee_percent')?.toString() || '0',
        gateway_fee_fixed: form.get('gateway_fee_fixed')?.toString() || '0',
        track_inventory: form.get('track_inventory') === 'true',
        stock_quantity: form.get('stock_quantity')?.toString() || '0',
        stock_min_alert: form.get('stock_min_alert')?.toString() || '0',
        unit_of_measure: form.get('unit_of_measure')?.toString() || 'un'
      };

      await apiRequest(
        `/invoices/products/${productId}/`,
        { method: 'PUT', body: productData },
        { cookies, org: locals.org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error updating product:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  },

  delete: async ({ request, locals, cookies }) => {
    try {
      const form = await request.formData();
      const productId = form.get('productId')?.toString();

      if (!productId) {
        return fail(400, { error: 'ID do produto é obrigatório' });
      }

      await apiRequest(
        `/invoices/products/${productId}/`,
        { method: 'DELETE' },
        { cookies, org: locals.org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error deleting product:', err);
      return fail(400, { error: err.message || 'Falha na operação' });
    }
  }
};
