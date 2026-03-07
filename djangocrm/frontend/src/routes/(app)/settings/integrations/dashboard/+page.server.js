import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  const period = url.searchParams.get('period') || '7d';

  try {
    const [integrations, metrics] = await Promise.all([
      apiRequest('/integrations/', {}, { cookies }),
      apiRequest(`/integrations/metrics/?period=${period}`, {}, { cookies }).catch(() => null),
    ]);

    return {
      integrations: integrations?.results || integrations || [],
      metrics: metrics || {},
      period,
      error: null,
    };
  } catch (err) {
    return { integrations: [], metrics: {}, period, error: err?.message || 'Falha ao carregar dashboard.' };
  }
}
