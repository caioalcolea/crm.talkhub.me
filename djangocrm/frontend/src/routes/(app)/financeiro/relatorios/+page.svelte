<script>
  import { goto } from '$app/navigation';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { PageHeader } from '$lib/components/layout';
  import * as Tabs from '$lib/components/ui/tabs/index.js';

  let { data } = $props();
  let activeTab = $state('plano');
  const currentYear = new Date().getFullYear();
  let cur = $derived($orgSettings.default_currency || 'BRL');

  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  function changeYear(ano) {
    goto(`/financeiro/relatorios?ano=${ano}`);
  }
</script>

<PageHeader title="Relatórios Financeiros" subtitle="Análise detalhada das finanças">
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

<div class="space-y-4 p-4 md:p-6">
  <Tabs.Root bind:value={activeTab}>
    <Tabs.List class="w-full">
      <Tabs.Trigger value="plano">Fluxo por Centro de Custo</Tabs.Trigger>
      <Tabs.Trigger value="mensal">Relatório Mensal</Tabs.Trigger>
    </Tabs.List>

    <!-- Tab 1: Fluxo por Centro de Custo -->
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
                    {row.meses[m] > 0 ? formatCurrency(row.meses[m], cur) : '-'}
                  </td>
                {/each}
                <td class="px-3 py-1.5 text-right font-mono font-bold">
                  {row.total > 0 ? formatCurrency(row.total, cur) : '-'}
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

    <!-- Tab 2: Relatório Mensal -->
    <Tabs.Content value="mensal" class="mt-4">
      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-muted/50 border-b">
              <th class="px-3 py-2 text-left font-medium">Mês</th>
              <th class="px-3 py-2 text-right font-medium">A Receber</th>
              <th class="px-3 py-2 text-right font-medium">A Pagar</th>
              <th class="hidden px-3 py-2 text-right font-medium sm:table-cell">Recebido</th>
              <th class="hidden px-3 py-2 text-right font-medium sm:table-cell">Pago</th>
              <th class="px-3 py-2 text-right font-medium">Saldo Real</th>
              <th class="hidden px-3 py-2 text-right font-medium md:table-cell">Saldo Previsto</th>
            </tr>
          </thead>
          <tbody>
            {#each data.mensal?.meses || [] as m}
              <tr class="border-b">
                <td class="px-3 py-2 font-medium">{months[m.mes - 1]}</td>
                <td class="px-3 py-2 text-right font-mono text-xs text-emerald-600">
                  {formatCurrency(m.receber_aberto, cur)}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs text-rose-600">
                  {formatCurrency(m.pagar_aberto, cur)}
                </td>
                <td class="hidden px-3 py-2 text-right font-mono text-xs sm:table-cell">
                  {formatCurrency(m.receber_pago, cur)}
                </td>
                <td class="hidden px-3 py-2 text-right font-mono text-xs sm:table-cell">
                  {formatCurrency(m.pagar_pago, cur)}
                </td>
                <td class="px-3 py-2 text-right font-mono text-xs font-bold {m.saldo_pago >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
                  {formatCurrency(m.saldo_pago, cur)}
                </td>
                <td class="hidden px-3 py-2 text-right font-mono text-xs md:table-cell {m.saldo_aberto >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
                  {formatCurrency(m.saldo_aberto, cur)}
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
