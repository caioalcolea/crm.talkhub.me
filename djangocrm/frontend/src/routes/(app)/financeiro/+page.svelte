<script>
  import { goto } from '$app/navigation';
  import { KPICard } from '$lib/components/dashboard';
  import { CashFlowChart, StatusBadge } from '$lib/components/financeiro';
  import { PageHeader } from '$lib/components/layout';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';
  import {
    ArrowDownCircle,
    ArrowUpCircle,
    Wallet,
    AlertTriangle,
    TrendingUp,
    TrendingDown
  } from '@lucide/svelte';

  let { data } = $props();

  const d = $derived(data.dashboard);
  const currentYear = new Date().getFullYear();
  let cur = $derived($orgSettings.default_currency || 'BRL');

  function changeYear(ano) {
    goto(`/financeiro?ano=${ano}`);
  }
</script>

<PageHeader title="Painel Financeiro" subtitle="Visão geral das contas a pagar e receber">
  {#snippet actions()}
    <select
      value={data.ano}
      onchange={(e) => changeYear(e.target.value)}
      class="border-input bg-background rounded-md border px-3 py-1.5 text-sm"
    >
      {#each Array.from({ length: 5 }, (_, i) => currentYear - 2 + i) as year}
        <option value={year}>{year}</option>
      {/each}
    </select>
  {/snippet}
</PageHeader>

<div class="space-y-6 p-4 md:p-6">
  <!-- KPI Cards -->
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
    <button class="cursor-pointer text-left" onclick={() => goto('/financeiro/receber')}>
      <KPICard
        label="A Receber"
        value={formatCurrency(d.total_receber, cur)}
        accentColor="emerald"
      >
        {#snippet icon({ class: cls })}
          <ArrowDownCircle class={cls} />
        {/snippet}
      </KPICard>
    </button>

    <button class="cursor-pointer text-left" onclick={() => goto('/financeiro/pagar')}>
      <KPICard
        label="A Pagar"
        value={formatCurrency(d.total_pagar, cur)}
        accentColor="rose"
      >
        {#snippet icon({ class: cls })}
          <ArrowUpCircle class={cls} />
        {/snippet}
      </KPICard>
    </button>

    <KPICard
      label="Recebido no Mês"
      value={formatCurrency(d.recebido_no_mes, cur)}
      accentColor="blue"
    >
      {#snippet icon({ class: cls })}
        <TrendingUp class={cls} />
      {/snippet}
    </KPICard>

    <KPICard
      label="Pago no Mês"
      value={formatCurrency(d.pago_no_mes, cur)}
      accentColor="orange"
    >
      {#snippet icon({ class: cls })}
        <TrendingDown class={cls} />
      {/snippet}
    </KPICard>

    <KPICard
      label="Vencido"
      value={formatCurrency(d.total_vencido, cur)}
      accentColor="amber"
    >
      {#snippet icon({ class: cls })}
        <AlertTriangle class={cls} />
      {/snippet}
    </KPICard>

    <KPICard
      label="Saldo do Mês"
      value={formatCurrency(d.saldo, cur)}
      accentColor={d.saldo >= 0 ? 'emerald' : 'rose'}
    >
      {#snippet icon({ class: cls })}
        <Wallet class={cls} />
      {/snippet}
    </KPICard>
  </div>

  <!-- Cash Flow Chart -->
  <div class="rounded-lg border p-4">
    <h2 class="mb-4 text-lg font-semibold">Fluxo de Caixa Mensal - {data.ano}</h2>
    <CashFlowChart data={d.fluxo_mensal || []} />
  </div>

  <!-- Last 10 Transactions -->
  <div class="rounded-lg border p-4">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold">Últimas Transações</h2>
      <a href="/financeiro/lancamentos" class="text-primary text-sm hover:underline">
        Ver todos
      </a>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-muted/50 border-b">
            <th class="px-3 py-2 text-left font-medium">Descrição</th>
            <th class="px-3 py-2 text-left font-medium">Tipo</th>
            <th class="px-3 py-2 text-right font-medium">Valor</th>
            <th class="hidden px-3 py-2 text-left font-medium sm:table-cell">Parcelas</th>
            <th class="px-3 py-2 text-left font-medium">Status</th>
            <th class="hidden px-3 py-2 text-left font-medium md:table-cell">Vencimento</th>
          </tr>
        </thead>
        <tbody>
          {#each d.ultimas_transacoes || [] as tx (tx.id)}
            <tr
              class="hover:bg-muted/30 cursor-pointer border-b transition-colors"
              onclick={() => goto(`/financeiro/lancamentos/${tx.id}`)}
            >
              <td class="max-w-[200px] truncate px-3 py-2 font-medium">{tx.descricao}</td>
              <td class="px-3 py-2"><StatusBadge status={tx.tipo} /></td>
              <td class="px-3 py-2 text-right font-mono text-xs">
                {formatCurrency(tx.valor_convertido, cur)}
              </td>
              <td class="hidden px-3 py-2 text-xs sm:table-cell">{tx.parcelas_pagas}</td>
              <td class="px-3 py-2"><StatusBadge status={tx.status} tipo={tx.tipo} /></td>
              <td class="hidden px-3 py-2 text-xs md:table-cell">{formatDate(tx.data_primeiro_vencimento)}</td>
            </tr>
          {:else}
            <tr>
              <td colspan="6" class="text-muted-foreground px-3 py-8 text-center">
                Nenhuma transação encontrada.
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</div>
