<script>
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';

  import { PageHeader } from '$lib/components/layout';
  import { Button } from '$lib/components/ui/button';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';

  /** @type {{ data: import('./$types').PageData }} */
  let { data } = $props();

  const dashboard = $derived(data.dashboard);
  const revenue = $derived(data.revenue);
  const aging = $derived(data.aging);
  const filters = $derived(data.filters);
  const productMargin = $derived(data.productMargin);
  const inventory = $derived(data.inventory);
  const topProducts = $derived(data.topProducts);

  const orgCurrency = $derived($orgSettings.default_currency || 'BRL');

  // Group by options
  const GROUP_BY_OPTIONS = [
    { value: 'day', label: 'Diário' },
    { value: 'week', label: 'Semanal' },
    { value: 'month', label: 'Mensal' },
    { value: 'year', label: 'Anual' }
  ];

  // Filter handlers
  async function updateFilters(newFilters) {
    const url = new URL($page.url);

    if (newFilters.startDate) url.searchParams.set('start_date', newFilters.startDate);
    if (newFilters.endDate) url.searchParams.set('end_date', newFilters.endDate);
    if (newFilters.groupBy) url.searchParams.set('group_by', newFilters.groupBy);

    await goto(url.toString(), { replaceState: true, invalidateAll: true });
  }

  // Status colors - using design system tokens
  function getStatusColor(status) {
    const colors = {
      Draft: 'bg-[var(--text-tertiary)]',
      Sent: 'bg-[var(--stage-contacted)]',
      Viewed: 'bg-[var(--stage-qualified)]',
      Partially_Paid: 'bg-[var(--stage-negotiation)]',
      Paid: 'bg-[var(--color-success-default)]',
      Overdue: 'bg-[var(--color-negative-default)]',
      Cancelled: 'bg-[var(--text-tertiary)]'
    };
    return colors[status] || 'bg-[var(--text-tertiary)]';
  }
</script>

<div class="flex flex-col gap-6 p-6">
  <!-- Header -->
  <PageHeader title="Relatórios de Faturas">
    {#snippet actions()}
      <Button variant="ghost" size="sm" onclick={() => goto('/invoices')}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="mr-2"
        >
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Faturas
      </Button>
    {/snippet}
  </PageHeader>

  <!-- Summary Cards -->
  <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
    <!-- Total Invoiced -->
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-[var(--text-secondary)]">Total Faturado</p>
          <p class="mt-1 text-2xl font-bold text-[var(--text-primary)]">
            {formatCurrency(Number(dashboard.summary?.total_invoiced || 0), orgCurrency)}
          </p>
        </div>
        <div
          class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary-light)]"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="text-[var(--color-primary-default)]"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Total Paid -->
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-[var(--text-secondary)]">Total Recebido</p>
          <p class="mt-1 text-2xl font-bold text-[var(--color-success-default)]">
            {formatCurrency(Number(dashboard.summary?.total_paid || 0), orgCurrency)}
          </p>
        </div>
        <div
          class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-success-light)]"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="text-[var(--color-success-default)]"
          >
            <line x1="12" y1="1" x2="12" y2="23" />
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Outstanding -->
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-[var(--text-secondary)]">Em Aberto</p>
          <p class="mt-1 text-2xl font-bold text-[var(--color-primary-default)]">
            {formatCurrency(Number(dashboard.summary?.total_due || 0), orgCurrency)}
          </p>
        </div>
        <div
          class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary-light)]"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="text-[var(--color-primary-default)]"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Overdue -->
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-[var(--text-secondary)]">
            Vencido ({dashboard.overdue?.count || 0})
          </p>
          <p class="mt-1 text-2xl font-bold text-[var(--color-negative-default)]">
            {formatCurrency(Number(dashboard.overdue?.amount || 0), orgCurrency)}
          </p>
        </div>
        <div
          class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-negative-light)]"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="text-[var(--color-negative-default)]"
          >
            <path
              d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
            />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>
      </div>
    </div>
  </div>

  <!-- Recent Activity & Status -->
  <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
    <!-- Recent Activity -->
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <h3 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Últimos 30 Dias</h3>
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-[var(--text-secondary)]">Receita Recebida</span>
          <span class="font-medium text-[var(--color-success-default)]">
            {formatCurrency(Number(dashboard.recent_activity?.revenue_30d || 0), orgCurrency)}
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[var(--text-secondary)]">Faturas Criadas</span>
          <span class="font-medium text-[var(--text-primary)]"
            >{dashboard.recent_activity?.invoices_created_30d || 0}</span
          >
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[var(--text-secondary)]">Faturas Pagas</span>
          <span class="font-medium text-[var(--text-primary)]"
            >{dashboard.recent_activity?.invoices_paid_30d || 0}</span
          >
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[var(--text-secondary)]">Total Faturado</span>
          <span class="font-medium text-[var(--text-primary)]">
            {formatCurrency(Number(dashboard.recent_activity?.invoiced_30d || 0), orgCurrency)}
          </span>
        </div>
      </div>
    </div>

    <!-- Status Breakdown -->
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <h3 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Status das Faturas</h3>
      <div class="space-y-3">
        {#each Object.entries(dashboard.status_counts || {}) as [status, count]}
          <div class="flex items-center gap-3">
            <div class="h-3 w-3 rounded-full {getStatusColor(status)}"></div>
            <span class="flex-1 text-[var(--text-secondary)]">{status.replace('_', ' ')}</span>
            <span class="font-medium text-[var(--text-primary)]">{count}</span>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Revenue Chart Section -->
  <div
    class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
  >
    <div class="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
      <h3 class="text-lg font-semibold text-[var(--text-primary)]">Receita ao Longo do Tempo</h3>
      <div class="flex flex-wrap gap-3">
        <input
          type="date"
          value={filters.startDate}
          onchange={(e) =>
            updateFilters({
              ...filters,
              startDate: /** @type {HTMLInputElement} */ (e.target).value
            })}
          class="rounded-lg border border-[var(--border-default)] bg-[var(--surface-default)] px-3 py-1.5 text-sm text-[var(--text-primary)]"
        />
        <input
          type="date"
          value={filters.endDate}
          onchange={(e) =>
            updateFilters({
              ...filters,
              endDate: /** @type {HTMLInputElement} */ (e.target).value
            })}
          class="rounded-lg border border-[var(--border-default)] bg-[var(--surface-default)] px-3 py-1.5 text-sm text-[var(--text-primary)]"
        />
        <select
          value={filters.groupBy}
          onchange={(e) =>
            updateFilters({
              ...filters,
              groupBy: /** @type {HTMLSelectElement} */ (e.target).value
            })}
          class="rounded-lg border border-[var(--border-default)] bg-[var(--surface-default)] px-3 py-1.5 text-sm text-[var(--text-primary)]"
        >
          {#each GROUP_BY_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>
    </div>

    {#if revenue.data && revenue.data.length > 0}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-[var(--border-default)]">
              <th class="py-2 text-left font-medium text-[var(--text-secondary)]">Período</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Faturas</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Receita</th>
            </tr>
          </thead>
          <tbody>
            {#each revenue.data as item}
              <tr class="border-b border-[var(--border-default)] last:border-b-0">
                <td class="py-3 text-[var(--text-primary)]">{formatDate(item.period)}</td>
                <td class="py-3 text-right text-[var(--text-secondary)]">{item.count}</td>
                <td class="py-3 text-right font-medium text-[var(--color-success-default)]">
                  {formatCurrency(Number(item.revenue), orgCurrency)}
                </td>
              </tr>
            {/each}
          </tbody>
          <tfoot>
            <tr class="border-t border-[var(--border-default)] bg-[var(--surface-sunken)]">
              <td class="py-3 font-medium text-[var(--text-primary)]">Total</td>
              <td class="py-3 text-right font-medium text-[var(--text-primary)]"
                >{revenue.total?.count || 0}</td
              >
              <td class="py-3 text-right font-bold text-[var(--color-success-default)]">
                {formatCurrency(Number(revenue.total?.revenue || 0), orgCurrency)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    {:else}
      <div class="py-8 text-center text-[var(--text-secondary)]">
        Nenhum dado de receita para o período selecionado
      </div>
    {/if}
  </div>

  <!-- Aging Report -->
  <div
    class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
  >
    <h3 class="mb-6 text-lg font-semibold text-[var(--text-primary)]">Contas a Receber por Vencimento</h3>

    <div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-5">
      <!-- Current -->
      <div class="rounded-lg bg-[var(--color-success-light)] p-4">
        <p class="text-sm font-medium text-[var(--color-success-default)]">Atual</p>
        <p class="mt-1 text-xl font-bold text-[var(--color-success-default)]">
          {formatCurrency(Number(aging.current?.amount || 0), orgCurrency)}
        </p>
        <p class="text-sm text-[var(--color-success-default)]/80">
          {aging.current?.count || 0} faturas
        </p>
      </div>

      <!-- 1-30 Dias -->
      <div class="rounded-lg bg-[var(--stage-negotiation-bg)] p-4">
        <p class="text-sm font-medium text-[var(--stage-negotiation)]">1-30 Dias</p>
        <p class="mt-1 text-xl font-bold text-[var(--stage-negotiation)]">
          {formatCurrency(Number(aging['1_30_days']?.amount || 0), orgCurrency)}
        </p>
        <p class="text-sm text-[var(--stage-negotiation)]/80">
          {aging['1_30_days']?.count || 0} faturas
        </p>
      </div>

      <!-- 31-60 Dias -->
      <div class="rounded-lg bg-[var(--color-primary-light)] p-4">
        <p class="text-sm font-medium text-[var(--color-primary-default)]">31-60 Dias</p>
        <p class="mt-1 text-xl font-bold text-[var(--color-primary-default)]">
          {formatCurrency(Number(aging['31_60_days']?.amount || 0), orgCurrency)}
        </p>
        <p class="text-sm text-[var(--color-primary-default)]/80">
          {aging['31_60_days']?.count || 0} faturas
        </p>
      </div>

      <!-- 61-90 Dias -->
      <div class="rounded-lg bg-[var(--color-negative-light)] p-4">
        <p class="text-sm font-medium text-[var(--color-negative-default)]">61-90 Dias</p>
        <p class="mt-1 text-xl font-bold text-[var(--color-negative-default)]">
          {formatCurrency(Number(aging['61_90_days']?.amount || 0), orgCurrency)}
        </p>
        <p class="text-sm text-[var(--color-negative-default)]/80">
          {aging['61_90_days']?.count || 0} faturas
        </p>
      </div>

      <!-- Mais de 90 Dias -->
      <div class="rounded-lg bg-[var(--color-negative-default)]/20 p-4">
        <p class="text-sm font-medium text-[var(--color-negative-default)]">Mais de 90 Dias</p>
        <p class="mt-1 text-xl font-bold text-[var(--color-negative-default)]">
          {formatCurrency(Number(aging['over_90_days']?.amount || 0), orgCurrency)}
        </p>
        <p class="text-sm text-[var(--color-negative-default)]/80">
          {aging['over_90_days']?.count || 0} faturas
        </p>
      </div>
    </div>

    <!-- Total Outstanding -->
    <div class="flex items-center justify-between border-t border-[var(--border-default)] pt-4">
      <span class="font-medium text-[var(--text-secondary)]">Total em Aberto</span>
      <div class="text-right">
        <p class="text-2xl font-bold text-[var(--text-primary)]">
          {formatCurrency(Number(aging.total?.amount || 0), orgCurrency)}
        </p>
        <p class="text-sm text-[var(--text-secondary)]">{aging.total?.count || 0} faturas</p>
      </div>
    </div>
  </div>

  <!-- Estimates Summary -->
  <div
    class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
  >
    <h3 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Visão Geral de Orçamentos</h3>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-lg bg-[var(--color-primary-light)] p-4 text-center">
        <p class="text-3xl font-bold text-[var(--color-primary-default)]">
          {dashboard.estimates?.pending || 0}
        </p>
        <p class="mt-1 text-sm text-[var(--color-primary-default)]">Pendente</p>
      </div>
      <div class="rounded-lg bg-[var(--color-success-light)] p-4 text-center">
        <p class="text-3xl font-bold text-[var(--color-success-default)]">
          {dashboard.estimates?.accepted || 0}
        </p>
        <p class="mt-1 text-sm text-[var(--color-success-default)]">Aceito</p>
      </div>
      <div class="rounded-lg bg-[var(--color-negative-light)] p-4 text-center">
        <p class="text-3xl font-bold text-[var(--color-negative-default)]">
          {dashboard.estimates?.declined || 0}
        </p>
        <p class="mt-1 text-sm text-[var(--color-negative-default)]">Recusado</p>
      </div>
    </div>
  </div>

  <!-- Product Margin Report -->
  {#if productMargin?.results?.length > 0}
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <h3 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Margem por Produto/Serviço</h3>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-[var(--border-default)]">
              <th class="py-2 text-left font-medium text-[var(--text-secondary)]">Produto</th>
              <th class="py-2 text-left font-medium text-[var(--text-secondary)]">Tipo</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Qtd Vendida</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Receita</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Taxas</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Custo</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Margem</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">%</th>
            </tr>
          </thead>
          <tbody>
            {#each productMargin.results as item}
              <tr class="border-b border-[var(--border-default)] last:border-b-0">
                <td class="py-3 text-[var(--text-primary)]">{item.name}</td>
                <td class="py-3">
                  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {item.product_type === 'service' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}">
                    {item.product_type === 'service' ? 'Serviço' : 'Produto'}
                  </span>
                </td>
                <td class="py-3 text-right text-[var(--text-secondary)]">{item.quantity_sold}</td>
                <td class="py-3 text-right text-[var(--text-primary)]">
                  {formatCurrency(Number(item.revenue), orgCurrency)}
                </td>
                <td class="py-3 text-right text-[var(--text-secondary)]">
                  {formatCurrency(Number(item.gateway_fees), orgCurrency)}
                </td>
                <td class="py-3 text-right text-[var(--text-secondary)]">
                  {formatCurrency(Number(item.cost), orgCurrency)}
                </td>
                <td class="py-3 text-right font-medium {Number(item.margin) >= 0 ? 'text-[var(--color-success-default)]' : 'text-[var(--color-negative-default)]'}">
                  {formatCurrency(Number(item.margin), orgCurrency)}
                </td>
                <td class="py-3 text-right font-medium {Number(item.margin_percent) >= 0 ? 'text-[var(--color-success-default)]' : 'text-[var(--color-negative-default)]'}">
                  {item.margin_percent}%
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  <!-- Inventory Summary -->
  {#if inventory?.results?.length > 0}
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-lg font-semibold text-[var(--text-primary)]">Resumo de Estoque</h3>
        <div class="flex gap-4 text-sm">
          <span class="text-[var(--text-secondary)]">
            {inventory.summary?.total_products || 0} produtos rastreados
          </span>
          <span class="font-medium text-[var(--text-primary)]">
            Valor: {formatCurrency(Number(inventory.summary?.total_stock_value || 0), orgCurrency)}
          </span>
          {#if (inventory.summary?.low_stock_count || 0) > 0}
            <span class="font-medium text-[var(--color-negative-default)]">
              {inventory.summary.low_stock_count} com estoque baixo
            </span>
          {/if}
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-[var(--border-default)]">
              <th class="py-2 text-left font-medium text-[var(--text-secondary)]">Produto</th>
              <th class="py-2 text-left font-medium text-[var(--text-secondary)]">SKU</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Estoque</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Mínimo</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Custo Unit.</th>
              <th class="py-2 text-right font-medium text-[var(--text-secondary)]">Valor Estoque</th>
            </tr>
          </thead>
          <tbody>
            {#each inventory.results as item}
              <tr class="border-b border-[var(--border-default)] last:border-b-0 {item.is_low_stock ? 'bg-[var(--color-negative-light)]/30' : ''}">
                <td class="py-3 text-[var(--text-primary)]">
                  {item.name}
                  {#if item.is_low_stock}
                    <span class="ml-2 text-xs text-[var(--color-negative-default)]">Estoque baixo</span>
                  {/if}
                </td>
                <td class="py-3 text-[var(--text-secondary)]">{item.sku || '—'}</td>
                <td class="py-3 text-right font-medium {item.is_low_stock ? 'text-[var(--color-negative-default)]' : 'text-[var(--text-primary)]'}">
                  {item.stock_quantity} {item.unit_of_measure}
                </td>
                <td class="py-3 text-right text-[var(--text-secondary)]">{item.stock_min_alert}</td>
                <td class="py-3 text-right text-[var(--text-secondary)]">
                  {formatCurrency(Number(item.cost_price), orgCurrency)}
                </td>
                <td class="py-3 text-right font-medium text-[var(--text-primary)]">
                  {formatCurrency(Number(item.stock_value), orgCurrency)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  <!-- Top Products -->
  {#if topProducts?.results?.length > 0}
    <div
      class="rounded-xl border border-[var(--border-default)] bg-[var(--surface-default)] p-6 shadow-sm"
    >
      <h3 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Top 10 Produtos por Receita</h3>
      <div class="space-y-3">
        {#each topProducts.results as item, i}
          {@const maxRevenue = Number(topProducts.results[0]?.revenue || 1)}
          {@const pct = (Number(item.revenue) / maxRevenue) * 100}
          <div class="flex items-center gap-3">
            <span class="w-6 text-right text-sm font-medium text-[var(--text-secondary)]">{i + 1}</span>
            <div class="flex-1">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-[var(--text-primary)]">{item.name}</span>
                <span class="text-sm text-[var(--text-secondary)]">
                  {formatCurrency(Number(item.revenue), orgCurrency)}
                </span>
              </div>
              <div class="mt-1 h-2 w-full rounded-full bg-[var(--surface-sunken)]">
                <div
                  class="h-2 rounded-full bg-[var(--color-primary-default)]"
                  style="width: {pct}%"
                ></div>
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
