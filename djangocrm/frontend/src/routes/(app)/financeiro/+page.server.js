import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const ano = url.searchParams.get('ano') || new Date().getFullYear().toString();

  try {
    const dashboard = await apiRequest(
      `/financeiro/reports/dashboard/?ano=${ano}`,
      {},
      { cookies, org }
    );

    return { dashboard, ano: parseInt(ano) };
  } catch (err) {
    console.error('Financeiro dashboard load error:', err);
    return {
      dashboard: {
        ano: parseInt(ano),
        total_receber: 0,
        total_pagar: 0,
        recebido_no_mes: 0,
        pago_no_mes: 0,
        total_vencido: 0,
        pct_vencidas: 0,
        saldo: 0,
        fluxo_mensal: [],
        ultimas_transacoes: []
      },
      ano: parseInt(ano)
    };
  }
}
