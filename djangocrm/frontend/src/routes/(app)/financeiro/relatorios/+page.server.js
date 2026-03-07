import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ url, locals, cookies }) {
  const org = locals.org;
  if (!org) throw error(401, 'Contexto de organização é obrigatório');

  const ano = url.searchParams.get('ano') || new Date().getFullYear().toString();

  try {
    const [dashboard, fluxo, mensal] = await Promise.all([
      apiRequest(`/financeiro/reports/dashboard/?ano=${ano}`, {}, { cookies, org }),
      apiRequest(`/financeiro/reports/fluxo-plano-contas/?ano=${ano}`, {}, { cookies, org }),
      apiRequest(`/financeiro/reports/relatorio-mensal/?ano=${ano}`, {}, { cookies, org })
    ]);

    return { dashboard, fluxo, mensal, ano: parseInt(ano) };
  } catch (err) {
    console.error('Relatorios load error:', err);
    return {
      dashboard: { total_receber: 0, total_pagar: 0, pago_no_mes: 0, total_vencido: 0, pct_vencidas: 0, saldo: 0 },
      fluxo: { planos: [] },
      mensal: { meses: [] },
      ano: parseInt(ano)
    };
  }
}
