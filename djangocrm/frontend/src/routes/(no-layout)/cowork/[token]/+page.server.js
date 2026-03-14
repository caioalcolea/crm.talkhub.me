/**
 * Public Cowork Guest Page
 *
 * Public view for guests to join a cowork room via invite token.
 * No authentication required. Uses SvelteKit's fetch for reliable SSR.
 */

import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, fetch }) {
  const { token } = params;

  if (!token) {
    throw error(400, 'Token do convite é obrigatório');
  }

  const apiBase = env.PUBLIC_DJANGO_API_URL || '';
  const url = `${apiBase}/api/public/cowork/join/${token}/`;

  try {
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const msg = data.error || data.detail || 'Erro ao validar convite';
      if (response.status === 404) throw error(404, msg);
      if (response.status === 410) throw error(410, msg);
      if (response.status === 429) throw error(429, 'Muitas tentativas. Aguarde um momento.');
      throw error(response.status, msg);
    }

    const data = await response.json();

    return {
      coworkToken: data.token,
      room: data.room,
      guest: data.guest,
      error: null,
    };
  } catch (err) {
    if (err?.status) throw err;
    console.error(`[cowork guest] Fetch failed: ${url}`, err?.message || err);
    throw error(500, 'Erro ao carregar sala de cowork');
  }
}
