import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, params }) {
  try {
    const [conversation, messages, channels] = await Promise.all([
      apiRequest(`/conversations/${params.id}/`, {}, { cookies }),
      apiRequest(`/conversations/${params.id}/messages/`, {}, { cookies }),
      apiRequest('/channels/', {}, { cookies }),
    ]);

    return {
      conversation: conversation || null,
      messages: messages?.results || messages || [],
      channels: channels?.results || channels || [],
      error: null,
    };
  } catch (err) {
    return { conversation: null, messages: [], channels: [], error: err?.message || 'Falha ao carregar conversa.' };
  }
}
