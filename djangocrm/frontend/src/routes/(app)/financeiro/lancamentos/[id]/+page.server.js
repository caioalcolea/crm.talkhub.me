import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  try {
    const [lancamento, formOptions] = await Promise.all([
      apiRequest(`/financeiro/lancamentos/${params.id}/`, {}, { cookies, org }),
      apiRequest('/financeiro/form-options/', {}, { cookies, org }),
    ]);

    return { lancamento, formOptions };
  } catch (err) {
    throw error(404, 'Lançamento não encontrado');
  }
}
