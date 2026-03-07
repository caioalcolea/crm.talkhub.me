/**
 * Campaign Analytics Page
 *
 * Django endpoints:
 *   GET /api/campaigns/<id>/analytics/
 *   GET /api/campaigns/<id>/recipients/
 */

import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies, params, url }) {
  const org = locals.org;
  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  const { id } = params;
  const recipientStatus = url.searchParams.get('recipient_status') || '';

  try {
    let recipientEndpoint = `/campaigns/${id}/recipients/?limit=50&offset=0`;
    if (recipientStatus) recipientEndpoint += `&status=${recipientStatus}`;

    const [analytics, recipientsData] = await Promise.all([
      apiRequest(`/campaigns/${id}/analytics/`, {}, cookies),
      apiRequest(recipientEndpoint, {}, cookies)
    ]);

    return {
      analytics: analytics || {},
      recipients: recipientsData?.results || [],
      recipientTotal: recipientsData?.total || 0,
      filters: { recipient_status: recipientStatus }
    };
  } catch (err) {
    console.error('Failed to load campaign analytics:', err);
    throw error(404, 'Campanha não encontrada');
  }
}
