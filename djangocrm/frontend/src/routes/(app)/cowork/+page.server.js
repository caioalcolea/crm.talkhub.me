/**
 * Sala Cowork — Room management and cowork session
 *
 * Django endpoints:
 *   GET  /api/cowork/rooms/
 *   POST /api/cowork/rooms/
 *   POST /api/cowork/auth/token/
 */

import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, cookies }) {
  const org = locals.org;
  if (!org) {
    throw error(401, 'Contexto de organização é obrigatório');
  }

  try {
    const rooms = await apiRequest('/cowork/rooms/', {}, cookies);
    return {
      rooms: rooms?.results || rooms || [],
      error: null,
    };
  } catch (err) {
    console.error('Failed to load cowork rooms:', err);
    return { rooms: [], error: err?.message || 'Falha ao carregar salas.' };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  createRoom: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get('name');
    const map_id = formData.get('map_id') || 'office_default';
    const max_participants = parseInt(formData.get('max_participants') || '25', 10);

    try {
      const room = await apiRequest('/cowork/rooms/', {
        method: 'POST',
        body: { name, map_id, max_participants }
      }, cookies);
      return { success: true, room, toast: 'Sala criada com sucesso!' };
    } catch (err) {
      return fail(400, { error: err?.message || 'Erro ao criar sala.' });
    }
  },

  deleteRoom: async ({ request, cookies }) => {
    const formData = await request.formData();
    const id = formData.get('id');

    try {
      await apiRequest(`/cowork/rooms/${id}/`, { method: 'DELETE' }, cookies);
      return { success: true, toast: 'Sala desativada.' };
    } catch (err) {
      return fail(400, { error: 'Erro ao desativar sala.' });
    }
  },

  createInvite: async ({ request, cookies }) => {
    const formData = await request.formData();
    const room_id = formData.get('room_id');
    const guest_name = formData.get('guest_name');
    const guest_email = formData.get('guest_email') || '';
    const hours = parseInt(formData.get('hours') || '24', 10);
    const max_uses = parseInt(formData.get('max_uses') || '1', 10);

    // Calculate expires_at
    const expires_at = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();

    try {
      const invite = await apiRequest(`/cowork/rooms/${room_id}/invites/`, {
        method: 'POST',
        body: { guest_name, guest_email, expires_at, max_uses }
      }, cookies);
      return { success: true, invite, toast: 'Convite criado!' };
    } catch (err) {
      return fail(400, { error: err?.message || 'Erro ao criar convite.' });
    }
  },

  getToken: async ({ request, cookies }) => {
    const formData = await request.formData();
    const room_id = formData.get('room_id');

    try {
      const result = await apiRequest('/cowork/auth/token/', {
        method: 'POST',
        body: { room_id }
      }, cookies);
      return { success: true, coworkToken: result.token, room: result.room };
    } catch (err) {
      return fail(400, { error: err?.message || 'Erro ao gerar token.' });
    }
  }
};
