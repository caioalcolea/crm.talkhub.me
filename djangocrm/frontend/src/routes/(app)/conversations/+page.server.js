import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  const channel = url.searchParams.get('channel') || '';
  const status = url.searchParams.get('status') || 'open';
  const assigned_to = url.searchParams.get('assigned_to') || '';
  const search = url.searchParams.get('search') || '';

  const params = new URLSearchParams();
  if (channel) params.set('channel', channel);
  if (status) params.set('status', status);
  if (assigned_to) params.set('assigned_to', assigned_to);
  if (search) params.set('search', search);

  const qs = params.toString();

  try {
    const [conversations, channels] = await Promise.all([
      apiRequest(`/conversations/${qs ? '?' + qs : ''}`, {}, { cookies }),
      apiRequest('/channels/', {}, { cookies }),
    ]);

    return {
      conversations: conversations?.results || conversations || [],
      channels: channels?.results || channels || [],
      filters: { channel, status, assigned_to, search },
      error: null,
    };
  } catch (err) {
    return {
      conversations: [],
      channels: [],
      filters: { channel, status, assigned_to, search },
      error: err?.message || 'Falha ao carregar conversas.',
    };
  }
}
