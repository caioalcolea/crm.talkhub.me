import { apiRequest, buildQueryParams } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  const channel = url.searchParams.get('channel') || '';
  const status = url.searchParams.get('status') || 'open';
  const assigned_to = url.searchParams.get('assigned_to') || '';
  const search = url.searchParams.get('search') || '';
  const is_group = url.searchParams.get('is_group') || '';

  const params = new URLSearchParams();
  if (channel) params.set('channel', channel);
  if (status) params.set('status', status);
  if (assigned_to) params.set('assigned_to', assigned_to);
  if (search) params.set('search', search);
  if (is_group) params.set('is_group', is_group);

  const qs = params.toString();

  try {
    const [conversations, channels] = await Promise.all([
      apiRequest(`/conversations/${qs ? '?' + qs : ''}`, {}, { cookies }),
      apiRequest('/channels/', {}, { cookies }),
    ]);

    return {
      conversations: conversations?.results || conversations || [],
      channels: channels?.results || channels || [],
      filters: { channel, status, assigned_to, search, is_group },
      error: null,
    };
  } catch (err) {
    return {
      conversations: [],
      channels: [],
      filters: { channel, status, assigned_to, search, is_group },
      error: err?.message || 'Falha ao carregar conversas.',
    };
  }
}
