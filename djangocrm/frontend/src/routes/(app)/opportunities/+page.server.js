/**
 * Opportunities List Page - API Version
 *
 * Migrated from Prisma to Django REST API
 * Django endpoint: GET /api/opportunities/
 */

import { error, fail } from '@sveltejs/kit';
import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, url }) {
  const userId = locals.user?.id;
  const org = locals.org;

  if (!userId) {
    return {
      opportunities: [],
      stats: { total: 0, totalValue: 0, wonValue: 0, pipeline: 0 },
      options: { accounts: [], contacts: [], users: [], teams: [], tags: [] },
      filters: {}
    };
  }

  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  // Parse view mode from URL
  const viewMode = url.searchParams.get('viewMode') || 'table';
  const pipelineId = url.searchParams.get('pipeline_id') || '';

  // Parse pagination params from URL
  const page = parseInt(url.searchParams.get('page') || '1');
  const limit = parseInt(url.searchParams.get('limit') || '10');

  // Parse filter params from URL
  const filters = {
    search: url.searchParams.get('search') || '',
    stage: url.searchParams.get('stage') || '',
    account: url.searchParams.get('account') || '',
    assigned_to: url.searchParams.getAll('assigned_to'),
    tags: url.searchParams.getAll('tags'),
    created_at_gte: url.searchParams.get('created_at_gte') || '',
    created_at_lte: url.searchParams.get('created_at_lte') || '',
    closed_on_gte: url.searchParams.get('closed_on_gte') || '',
    closed_on_lte: url.searchParams.get('closed_on_lte') || '',
    rotten: url.searchParams.get('rotten') || ''
  };

  try {
    // Build query parameters for Django API
    const queryParams = buildQueryParams({ page, limit });

    // Add filter params
    if (filters.search) queryParams.append('search', filters.search);
    if (filters.stage) queryParams.append('stage', filters.stage);
    if (filters.account) queryParams.append('account', filters.account);
    filters.assigned_to.forEach((id) => queryParams.append('assigned_to', id));
    filters.tags.forEach((id) => queryParams.append('tags', id));
    if (filters.created_at_gte) queryParams.append('created_at__gte', filters.created_at_gte);
    if (filters.created_at_lte) queryParams.append('created_at__lte', filters.created_at_lte);
    if (filters.closed_on_gte) queryParams.append('closed_on__gte', filters.closed_on_gte);
    if (filters.closed_on_lte) queryParams.append('closed_on__lte', filters.closed_on_lte);
    if (filters.rotten) queryParams.append('rotten', filters.rotten);

    const queryString = queryParams.toString();

    // Build kanban query params
    const kanbanQueryParams = new URLSearchParams();
    if (filters.search) kanbanQueryParams.append('search', filters.search);
    if (filters.stage) kanbanQueryParams.append('stage', filters.stage);
    if (filters.account) kanbanQueryParams.append('account', filters.account);
    filters.assigned_to.forEach((id) => kanbanQueryParams.append('assigned_to', id));
    if (pipelineId) kanbanQueryParams.append('pipeline_id', pipelineId);
    const kanbanQueryString = kanbanQueryParams.toString();

    // Fetch opportunities, teams/users, products, kanban data, and pipelines in parallel
    const [response, teamsUsersResponse, productsResponse, kanbanResponse, pipelinesResponse] = await Promise.all([
      apiRequest(`/opportunities/${queryString ? `?${queryString}` : ''}`, {}, { cookies, org }),
      apiRequest('/users/get-teams-and-users/', {}, { cookies, org }).catch((err) => {
        console.error('Failed to fetch teams/users:', err);
        return { teams: [], profiles: [] };
      }),
      apiRequest('/invoices/products/?is_active=true&limit=200', {}, { cookies, org }).catch(
        (err) => {
          console.error('Failed to fetch products:', err);
          return { results: [] };
        }
      ),
      viewMode === 'kanban'
        ? apiRequest(
            `/opportunities/kanban/${kanbanQueryString ? `?${kanbanQueryString}` : ''}`,
            {},
            { cookies, org }
          ).catch((err) => {
            console.error('Failed to fetch kanban data:', err);
            return null;
          })
        : Promise.resolve(null),
      apiRequest('/opportunities/pipelines/', {}, { cookies, org }).catch((err) => {
        console.error('Failed to fetch pipelines:', err);
        return [];
      })
    ]);

    // Handle Django response structure
    let opportunities = [];
    if (response.opportunities) {
      opportunities = response.opportunities;
    } else if (Array.isArray(response)) {
      opportunities = response;
    } else if (response.results) {
      opportunities = response.results;
    }

    // Extract options from API response
    const accounts = (response.accounts_list || []).map((acc) => ({
      id: acc.id,
      name: acc.name
    }));

    const contacts = (response.contacts_list || []).map((contact) => ({
      id: contact.id,
      name: `${contact.first_name || ''} ${contact.last_name || ''}`.trim(),
      email: contact.email
    }));

    const tags = (response.tags || []).map((tag) => ({
      id: tag.id,
      name: tag.name,
      slug: tag.slug,
      color: tag.color || 'blue'
    }));

    // Extract users (profiles) from teams/users response
    const users = (teamsUsersResponse.profiles || []).map((profile) => ({
      id: profile.id,
      name: profile.user_details?.email || 'N/A',
      email: profile.user_details?.email || ''
    }));

    // Extract teams from teams/users response
    const teams = (teamsUsersResponse.teams || []).map((team) => ({
      id: team.id,
      name: team.name
    }));

    // Extract products from products response
    const products = (productsResponse.results || []).map((product) => ({
      id: product.id,
      name: product.name,
      sku: product.sku,
      price: product.price ? Number(product.price) : 0,
      currency: product.currency,
      category: product.category
    }));

    // Transform Django opportunities with all fields
    const transformedOpportunities = opportunities.map((opp) => ({
      id: opp.id,
      name: opp.name,
      amount: opp.amount ? Number(opp.amount) : null,
      stage: opp.stage,
      pipeline_stage: opp.pipeline_stage?.id || opp.pipeline_stage || null,
      opportunityType: opp.opportunity_type,
      currency: opp.currency,
      probability: opp.probability,
      leadSource: opp.lead_source,
      description: opp.description,
      closedOn: opp.closed_on,
      createdAt: opp.created_at,
      updatedAt: opp.updated_at,
      isActive: opp.is_active,
      createdOnArrow: opp.created_on_arrow,

      // Account
      account: opp.account
        ? {
            id: opp.account.id,
            name: opp.account.name,
            type: opp.account.type || opp.account.account_type
          }
        : null,

      // Assigned users (multi)
      assignedTo: (opp.assigned_to || []).map((profile) => ({
        id: profile.id,
        name: profile.user_details?.email || 'Sem atribuição',
        email: profile.user_details?.email || ''
      })),

      // Teams
      teams: (opp.teams || []).map((team) => ({
        id: team.id,
        name: team.name
      })),

      // Contacts
      contacts: (opp.contacts || []).map((contact) => ({
        id: contact.id,
        firstName: contact.first_name,
        lastName: contact.last_name,
        email: contact.email
      })),

      // Tags
      tags: (opp.tags || []).map((tag) => ({
        id: tag.id,
        name: tag.name,
        slug: tag.slug
      })),

      // Closed by
      closedBy: opp.closed_by
        ? {
            id: opp.closed_by.id,
            name: opp.closed_by.user_details?.email || opp.closed_by.email
          }
        : null,

      // Line Items / Products
      lineItems: (opp.line_items || []).map((item) => ({
        id: item.id,
        productId: item.product?.id || null,
        productName: item.product?.name || item.name,
        name: item.name,
        description: item.description,
        quantity: item.quantity ? Number(item.quantity) : 1,
        unitPrice: item.unit_price ? Number(item.unit_price) : 0,
        discountType: item.discount_type,
        discountValue: item.discount_value ? Number(item.discount_value) : 0,
        discountAmount: item.discount_amount ? Number(item.discount_amount) : 0,
        subtotal: item.subtotal ? Number(item.subtotal) : 0,
        total: item.total ? Number(item.total) : 0,
        order: item.order || 0
      })),
      lineItemsTotal: opp.line_items_total ? Number(opp.line_items_total) : 0,
      amountSource: opp.amount_source || 'MANUAL',

      // Deal Aging
      stageChangedAt: opp.stage_changed_at,
      daysInStage: opp.days_in_stage ?? 0,
      agingStatus: opp.aging_status || 'green',

      // Counts
      _count: {
        tasks: opp.task_count || 0,
        events: opp.event_count || 0
      }
    }));

    // Calculate stats
    const stats = {
      total: transformedOpportunities.length,
      totalValue: transformedOpportunities.reduce((sum, opp) => sum + (opp.amount || 0), 0),
      wonValue: transformedOpportunities
        .filter((opp) => opp.stage === 'CLOSED_WON')
        .reduce((sum, opp) => sum + (opp.amount || 0), 0),
      pipeline: transformedOpportunities
        .filter((opp) => !['CLOSED_WON', 'CLOSED_LOST'].includes(opp.stage))
        .reduce((sum, opp) => sum + (opp.amount || 0), 0)
    };

    // Get total count from response
    const total = response.opportunities_count || response.count || transformedOpportunities.length;

    // Extract pipelines list
    const pipelines = Array.isArray(pipelinesResponse)
      ? pipelinesResponse
      : pipelinesResponse?.pipelines || pipelinesResponse?.results || [];

    return {
      opportunities: transformedOpportunities,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit) || 1
      },
      stats,
      options: {
        accounts,
        contacts,
        tags,
        users,
        teams,
        products
      },
      filters,
      viewMode,
      pipelineId: pipelineId || kanbanResponse?.pipeline?.id || '',
      kanbanData: kanbanResponse,
      pipelines
    };
  } catch (err) {
    console.error('Error loading opportunities from API:', err);
    throw error(500, `Falha ao carregar oportunidades: ${err.message}`);
  }
}

/**
 * Parse JSON array from form data
 * @param {FormData} formData
 * @param {string} key
 * @returns {string[]}
 */
function parseJsonArray(formData, key) {
  const value = formData.get(key)?.toString();
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const org = locals.org;

      if (!org) {
        return fail(400, { message: 'Contexto de organização é obrigatório' });
      }

      // Build opportunity data for Django API with all fields
      const opportunityData = {
        name: formData.get('name')?.toString() || '',
        amount: formData.get('amount') ? Number(formData.get('amount')) : null,
        probability: formData.get('probability') ? Number(formData.get('probability')) : 0,
        stage: formData.get('stage')?.toString() || 'PROSPECTING',
        opportunity_type: formData.get('opportunityType')?.toString() || null,
        currency: formData.get('currency')?.toString() || null,
        lead_source: formData.get('leadSource')?.toString() || null,
        closed_on: formData.get('closedOn')?.toString() || null,
        description: formData.get('description')?.toString() || '',
        account: formData.get('accountId')?.toString() || null,
        contacts: parseJsonArray(formData, 'contacts'),
        assigned_to: parseJsonArray(formData, 'assignedTo'),
        teams: parseJsonArray(formData, 'teams'),
        tags: parseJsonArray(formData, 'tags')
      };

      // Pipeline stage
      const pipelineStageId = formData.get('pipelineStageId')?.toString() || null;
      if (pipelineStageId) opportunityData.pipeline_stage = pipelineStageId;

      // Create via API
      await apiRequest(
        '/opportunities/',
        { method: 'POST', body: opportunityData },
        { cookies, org }
      );

      return { success: true, message: 'Oportunidade criada com sucesso' };
    } catch (err) {
      console.error('Error creating opportunity:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  update: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const org = locals.org;

      if (!opportunityId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      // Build opportunity data only for fields that are present in the form
      // This prevents overwriting existing values with nulls during inline edits
      /** @type {Record<string, any>} */
      const opportunityData = {};

      // Simple string fields
      if (formData.has('name')) {
        opportunityData.name = formData.get('name')?.toString() || '';
      }
      if (formData.has('stage')) {
        opportunityData.stage = formData.get('stage')?.toString() || 'PROSPECTING';
      }
      if (formData.has('opportunityType')) {
        opportunityData.opportunity_type = formData.get('opportunityType')?.toString() || null;
      }
      if (formData.has('currency')) {
        opportunityData.currency = formData.get('currency')?.toString() || null;
      }
      if (formData.has('leadSource')) {
        opportunityData.lead_source = formData.get('leadSource')?.toString() || null;
      }
      if (formData.has('closedOn')) {
        opportunityData.closed_on = formData.get('closedOn')?.toString() || null;
      }
      if (formData.has('description')) {
        opportunityData.description = formData.get('description')?.toString() || '';
      }
      if (formData.has('accountId')) {
        opportunityData.account = formData.get('accountId')?.toString() || null;
      }
      if (formData.has('pipelineStageId')) {
        opportunityData.pipeline_stage = formData.get('pipelineStageId')?.toString() || null;
      }

      // Number fields
      if (formData.has('amount')) {
        opportunityData.amount = formData.get('amount') ? Number(formData.get('amount')) : null;
      }
      if (formData.has('probability')) {
        opportunityData.probability = formData.get('probability')
          ? Number(formData.get('probability'))
          : 0;
      }

      // Array fields (M2M relationships)
      if (formData.has('contacts')) {
        opportunityData.contacts = parseJsonArray(formData, 'contacts');
      }
      if (formData.has('assignedTo')) {
        opportunityData.assigned_to = parseJsonArray(formData, 'assignedTo');
      }
      if (formData.has('teams')) {
        opportunityData.teams = parseJsonArray(formData, 'teams');
      }
      if (formData.has('tags')) {
        opportunityData.tags = parseJsonArray(formData, 'tags');
      }

      // Update via API
      await apiRequest(
        `/opportunities/${opportunityId}/`,
        { method: 'PATCH', body: opportunityData },
        { cookies, org }
      );

      return { success: true, message: 'Oportunidade atualizada com sucesso' };
    } catch (err) {
      console.error('Error updating opportunity:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  updateStage: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const newStage = formData.get('stage')?.toString();
      const org = locals.org;

      if (!opportunityId || !newStage || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      // Update via API with PATCH (partial update)
      await apiRequest(
        `/opportunities/${opportunityId}/`,
        { method: 'PATCH', body: { stage: newStage } },
        { cookies, org }
      );

      return { success: true, message: `Estágio atualizado para ${newStage}` };
    } catch (err) {
      console.error('Error updating opportunity stage:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  delete: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const userId = locals.user?.id;
      const org = locals.org;

      if (!opportunityId || !userId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      // Delete via API
      await apiRequest(`/opportunities/${opportunityId}/`, { method: 'DELETE' }, { cookies, org });

      return { success: true, message: 'Oportunidade excluída com sucesso' };
    } catch (err) {
      console.error('Error deleting opportunity:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  // ==========================================================================
  // KANBAN MOVE ACTION
  // ==========================================================================

  move: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const org = locals.org;

      if (!opportunityId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      /** @type {Record<string, any>} */
      const moveData = {};

      // Pipeline mode: stage UUID
      const pipelineStageId = formData.get('pipelineStageId')?.toString();
      if (pipelineStageId) {
        moveData.pipeline_stage_id = pipelineStageId;
      }

      // Legacy mode: stage string
      const stage = formData.get('stage')?.toString();
      if (stage) {
        moveData.stage = stage;
      }

      // Kanban ordering hints
      const aboveId = formData.get('aboveId')?.toString();
      const belowId = formData.get('belowId')?.toString();
      if (aboveId) moveData.above_id = aboveId;
      if (belowId) moveData.below_id = belowId;

      await apiRequest(
        `/opportunities/${opportunityId}/move/`,
        { method: 'PATCH', body: moveData },
        { cookies, org }
      );

      return { success: true };
    } catch (err) {
      console.error('Error moving opportunity:', err);
      return fail(400, { message: err.message || 'Falha ao mover' });
    }
  },

  // ==========================================================================
  // LINE ITEM ACTIONS
  // ==========================================================================

  addLineItem: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const org = locals.org;

      if (!opportunityId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      const lineItemData = {
        product_id: formData.get('productId')?.toString() || null,
        name: formData.get('name')?.toString() || '',
        description: formData.get('description')?.toString() || '',
        quantity: formData.get('quantity') ? Number(formData.get('quantity')) : 1,
        unit_price: formData.get('unitPrice') ? Number(formData.get('unitPrice')) : 0,
        discount_type: formData.get('discountType')?.toString() || '',
        discount_value: formData.get('discountValue') ? Number(formData.get('discountValue')) : 0,
        order: formData.get('order') ? Number(formData.get('order')) : 0
      };

      const response = await apiRequest(
        `/opportunities/${opportunityId}/line-items/`,
        { method: 'POST', body: lineItemData },
        { cookies, org }
      );

      return {
        success: true,
        message: 'Produto adicionado',
        lineItem: response.line_item,
        opportunityAmount: response.opportunity_amount
      };
    } catch (err) {
      console.error('Error adding line item:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  updateLineItem: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const lineItemId = formData.get('lineItemId')?.toString();
      const org = locals.org;

      if (!opportunityId || !lineItemId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      /** @type {Record<string, any>} */
      const lineItemData = {};

      if (formData.has('productId')) {
        lineItemData.product_id = formData.get('productId')?.toString() || null;
      }
      if (formData.has('name')) {
        lineItemData.name = formData.get('name')?.toString() || '';
      }
      if (formData.has('description')) {
        lineItemData.description = formData.get('description')?.toString() || '';
      }
      if (formData.has('quantity')) {
        lineItemData.quantity = Number(formData.get('quantity')) || 1;
      }
      if (formData.has('unitPrice')) {
        lineItemData.unit_price = Number(formData.get('unitPrice')) || 0;
      }
      if (formData.has('discountType')) {
        lineItemData.discount_type = formData.get('discountType')?.toString() || '';
      }
      if (formData.has('discountValue')) {
        lineItemData.discount_value = Number(formData.get('discountValue')) || 0;
      }
      if (formData.has('order')) {
        lineItemData.order = Number(formData.get('order')) || 0;
      }

      const response = await apiRequest(
        `/opportunities/${opportunityId}/line-items/${lineItemId}/`,
        { method: 'PUT', body: lineItemData },
        { cookies, org }
      );

      return {
        success: true,
        message: 'Produto atualizado',
        lineItem: response.line_item,
        opportunityAmount: response.opportunity_amount
      };
    } catch (err) {
      console.error('Error updating line item:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  deleteLineItem: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const lineItemId = formData.get('lineItemId')?.toString();
      const org = locals.org;

      if (!opportunityId || !lineItemId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      const response = await apiRequest(
        `/opportunities/${opportunityId}/line-items/${lineItemId}/`,
        { method: 'DELETE' },
        { cookies, org }
      );

      return {
        success: true,
        message: 'Produto removido',
        opportunityAmount: response.opportunity_amount
      };
    } catch (err) {
      console.error('Error deleting line item:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  },

  // ==========================================================================
  // CREATE INVOICE FROM OPPORTUNITY
  // ==========================================================================

  createInvoice: async ({ request, locals, cookies }) => {
    try {
      const formData = await request.formData();
      const opportunityId = formData.get('opportunityId')?.toString();
      const org = locals.org;

      if (!opportunityId || !org) {
        return fail(400, { message: 'Dados obrigatórios ausentes' });
      }

      const response = await apiRequest(
        `/invoices/from-opportunity/${opportunityId}/`,
        { method: 'POST' },
        { cookies, org }
      );

      return {
        success: true,
        message: 'Fatura criada com sucesso',
        invoiceId: response.invoice?.id
      };
    } catch (err) {
      console.error('Error creating invoice from opportunity:', err);
      return fail(400, { message: err.message || 'Falha na operação' });
    }
  }
};
