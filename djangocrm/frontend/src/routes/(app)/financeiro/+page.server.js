import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const ano = url.searchParams.get('ano') || new Date().getFullYear().toString();
  const now = new Date();
  const currentMonth = now.getMonth() + 1;

  try {
    const [dashboard, fluxoDiario] = await Promise.all([
      apiRequest(`/financeiro/reports/dashboard/?ano=${ano}`, {}, { cookies, org }),
      apiRequest(`/financeiro/reports/fluxo-diario/?ano=${ano}&mes=${currentMonth}`, {}, { cookies, org }),
    ]);

    return { dashboard, fluxoDiario, ano: parseInt(ano) };
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
        saldo_projetado_mes: 0,
        saldo_projetado_ano: 0,
        fluxo_mensal: [],
        ultimas_transacoes: []
      },
      fluxoDiario: { ano: parseInt(ano), mes: currentMonth, dias: [], resumo: {} },
      ano: parseInt(ano)
    };
  }
}
