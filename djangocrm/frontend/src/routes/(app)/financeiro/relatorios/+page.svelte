<script>
  import { goto } from '$app/navigation';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { KPICard } from '$lib/components/dashboard';
  import * as Tabs from '$lib/components/ui/tabs/index.js';
  import {
    ArrowDownCircle,
    ArrowUpCircle,
    Wallet,
    AlertTriangle,
    Percent,
    TrendingUp
  } from '@lucide/svelte';

  let { data } = $props();
  let activeTab = $state('dashboard');
  const currentYear = new Date().getFullYear();

  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  function changeYear(ano) {
    goto(`/financeiro/relatorios?ano=${ano}`);
  }

  const d = $derived(data.dashboard);
</script>

<div class="space-y-4 p-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Relatórios Financeiros</h1>
      <p class="text-muted-foreground text-sm">Análise detalhada das finanças</p>
    </div>
    <select
      value={data.ano}
      onchange={(e) => changeYear(e.target.value)}
      class="border-input bg-background rounded-md border px-3 py-1.5 text-sm"
    >
      {#each Array.from({ length: 5 }, (_, i) => currentYear - 2 + i) as year}
        <option value={year}>{year}</option>
      {/each}
    </select>
  </div>

  <Tabs.Root bind:value={activeTab}>
    <Tabs.List class="w-full">
      <Tabs.Trigger value="dashboard">Dashboard Geral</Tabs.Trigger>
      <Tabs.Trigger value="plano">Fluxo por Centro de Custo</Tabs.Trigger>
      <Tabs.Trigger value="mensal">Relatório Mensal</Tabs.Trigger>
    </Tabs.List>

    <!-- Tab 1: Dashboard -->
    <Tabs.Content value="dashboard" class="mt-4 space-y-4">
      <div class="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <KPICard label="Total a Receber" value={formatCurrency(d.total_receber, 'BRL')} accentColor="emerald">
          {#snippet icon({ class: cls })} <ArrowDownCircle class={cls} /> {/snippet}
        </KPICard>
        <KPICard label="Total a Pagar" value={formatCurrency(d.total_pagar, 'BRL')} accentColor="rose">
          {#snippet icon({ class: cls })} <ArrowUpCircle class={cls} /> {/snippet}
        </KPICard>
        <KPICard label="Pago no Mês" value={formatCurrency(d.pago_no_mes, 'BRL')} accentColor="blue">
          {#snippet icon({ class: cls })} <Wallet class={cls} /> {/snippet}
        </KPICard>
        <KPICard label="Total Vencido" value={formatCurrency(d.total_vencido, 'BRL')} accentColor="amber">
          {#snippet icon({ class: cls })} <AlertTriangle class={cls} /> {/snippet}
        </KPICard>
        <KPICard label="% Vencidas" value={`${d.pct_vencidas}%`} accentColor="orange">
          {#snippet icon({ class: cls })} <Percent class={cls} /> {/snippet}
        </KPICard>
        <KPICard label="Saldo" value={formatCurrency(d.saldo, 'BRL')} accentColor={d.saldo >= 0 ? 'emerald' : 'rose'}>
          {#snippet icon({ class: cls })} <TrendingUp class={cls} /> {/snippet}
        </KPICard>
      </div>
    </Tabs.Content>

    <!-- Tab 2: Fluxo por Centro de Custo -->
    <Tabs.Content value="plano" class="mt-4">
      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full text-xs">
          <thead>
            <tr class="bg-muted/50 border-b">
              <th class="sticky left-0 bg-muted/50 px-3 py-2 text-left font-medium">Centro de Custo</th>
              {#each months as m}
                <th class="min-w-[80px] px-2 py-2 text-right font-medium">{m}</th>
              {/each}
              <th class="px-3 py-2 text-right font-bold">Total</th>
            </tr>
          </thead>
          <tbody>
            {#each data.fluxo?.planos || [] as row}
              <tr class="border-b">
                <td class="bg-background sticky left-0 px-3 py-1.5">
                  <span class="text-muted-foreground">{row.grupo_codigo}</span>
                  <span class="ml-1 font-medium">{row.plano_nome}</span>
                </td>
                {#each Array.from({ length: 12 }, (_, i) => String(i + 1)) as m}
                  <td class="px-2 py-1.5 text-right font-mono">
                    {row.meses[m] > 0 ? formatCurrency(row.meses[m], 'BRL') : '-'}
                  </td>
                {/each}
                <td class="px-3 py-1.5 text-right font-mono font-bold">
                  {row.total > 0 ? formatCurrency(row.total, 'BRL') : '-'}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="14" class="text-muted-foreground px-3 py-8 text-center">
                  Nenhum dado encontrado para o período.
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </Tabs.Content>

    <!-- Tab 3: Relatório Mensal -->
    <Tabs.Content value="mensal" class="mt-4">
      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-muted/50 border-b">
              <th class="px-3 py-2 text-left font-medium">Mês</th>
              <th class="px-3 py-2 text-right font-medium">Receber (Aberto)</th>
              <th class="px-3 py-2 text-right font-medium">Pagar (Aberto)</th>
              <th class="px-3 py-2 text-right font-medium">Recebido</th>
              <th class="px-3 py-2 text-right font-medium">Pago</th>
              <th class="px-3 py-2 text-right font-medium">Saldo Pago</th>
              <th class="px-3 py-2 text-right font-medium">Saldo Aberto</th>
            </tr>
          </thead>
          <tbody>
            {#each data.mensal?.meses || [] as m}
              <tr class="border-b">
                <td class="px-3 py-2 font-medium">{months[m.mes - 1]}</td>
                <td class="px-3 py-2 text-right font-mono text-xs text-emerald-600">
                  {formatCurrency(m.receber_aberto, 'BRL')}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs text-rose-600">
                  {formatCurrency(m.pagar_aberto, 'BRL')}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs">
                  {formatCurrency(m.receber_pago, 'BRL')}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs">
                  {formatCurrency(m.pagar_pago, 'BRL')}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs font-bold {m.saldo_pago >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
                  {formatCurrency(m.saldo_pago, 'BRL')}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs {m.saldo_aberto >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
                  {formatCurrency(m.saldo_aberto, 'BRL')}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="7" class="text-muted-foreground px-3 py-8 text-center">
                  Nenhum dado encontrado.
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </Tabs.Content>
  </Tabs.Root>
</div>
