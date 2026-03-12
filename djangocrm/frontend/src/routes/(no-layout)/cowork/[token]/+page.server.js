/**
 * Public Cowork Guest Page
 *
 * Public view for guests to join a cowork room via invite token.
 * No authentication required.
 */

import { error } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, fetch }) {
  const { token } = params;

  if (!token) {
    throw error(400, 'Token do convite é obrigatório');
  }

  try {
    const response = await fetch(`/api/public/cowork/join/${token}/`);

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
    throw error(500, 'Erro ao carregar sala de cowork');
  }
}
