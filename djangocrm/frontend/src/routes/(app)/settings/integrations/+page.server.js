import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  try {
    const integrations = await apiRequest('/integrations/', {}, { cookies });
    return { integrations: integrations.results || integrations || [], error: null };
  } catch (err) {
    return { integrations: [], error: err?.message || 'Falha ao carregar integrações.' };
  }
}
