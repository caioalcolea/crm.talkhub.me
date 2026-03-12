/**
 * Public Cowork Guest Page
 *
 * Public view for guests to join a cowork room via invite token.
 * No authentication required. Uses absolute API URL to avoid SSR
 * fetch resolution issues with relative paths.
 */

import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';

const API_BASE_URL = `${env.PUBLIC_DJANGO_API_URL}/api`;

/** @type {import('./$types').PageServerLoad} */
export async function load({ params }) {
  const { token } = params;

  if (!token) {
    throw error(400, 'Token do convite é obrigatório');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/public/cowork/join/${token}/`, {
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      if (response.status === 404) {
        throw error(404, data.error || 'Convite não encontrado');
      }
      if (response.status === 410) {
        throw error(410, data.error || 'Convite expirado ou revogado');
      }
      throw error(response.status, data.error || 'Erro ao validar convite');
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
    console.error('[cowork guest] Failed to load:', err?.message || err);
    throw error(500, 'Erro ao carregar sala de cowork');
  }
}
