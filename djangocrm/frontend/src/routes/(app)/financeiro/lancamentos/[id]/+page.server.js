import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  try {
    const lancamento = await apiRequest(
      `/financeiro/lancamentos/${params.id}/`,
      {},
      { cookies, org }
    );

    return { lancamento };
  } catch (err) {
    throw error(404, 'Lançamento não encontrado');
  }
}
