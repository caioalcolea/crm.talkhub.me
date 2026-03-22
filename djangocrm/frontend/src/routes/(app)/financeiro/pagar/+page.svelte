<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { ParcelaTable } from '$lib/components/financeiro';
  import { PageHeader } from '$lib/components/layout';
  import { financeiro } from '$lib/api.js';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { Search, X, CheckCheck, ChevronDown, ChevronRight, Bell } from '@lucide/svelte';

  let { data } = $props();
  let searchInput = $state('');
  let vencimentoFrom = $state('');
  let vencimentoTo = $state('');
  let selectedIds = $state([]);
  let cur = $derived($orgSettings.default_currency || 'BRL');
  let reminderIds = $derived(new Set(data.reminderLancamentoIds || []));

  const MONTH_NAMES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

  $effect(() => {
    if (data?.filters?.search) searchInput = data.filters.search;
    if (data?.filters?.vencimento_from) vencimentoFrom = data.filters.vencimento_from;
    if (data?.filters?.vencimento_to) vencimentoTo = data.filters.vencimento_to;
  });

  function buildFilterParams(extra = {}) {
    const params = new URLSearchParams();
    if (searchInput) params.set('search', searchInput);
    if (data.filters.status) params.set('status', data.filters.status);
    if (vencimentoFrom) params.set('vencimento_from', vencimentoFrom);
    if (vencimentoTo) params.set('vencimento_to', vencimentoTo);
    for (const [k, v] of Object.entries(extra)) {
      if (v) params.set(k, v);
    }
    return params.toString();
  }

  // Group parcelas by competencia_ano/competencia_mes
  let groupedParcelas = $derived.by(() => {
    const groups = new Map();
    for (const p of data.parcelas) {
      const key = `${p.competencia_ano}-${String(p.competencia_mes).padStart(2, '0')}`;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          ano: p.competencia_ano,
          mes: p.competencia_mes,
          label: `${MONTH_NAMES[p.competencia_mes - 1]} ${p.competencia_ano}`,
          parcelas: [],
          total: 0,
          count: 0
        });
      }
      const g = groups.get(key);
      g.parcelas.push(p);
      g.total += parseFloat(p.valor_parcela_convertido || 0);
      g.count++;
    }
    return [...groups.values()].sort((a, b) => a.key.localeCompare(b.key));
  });

  // Auto-expand current/overdue months, collapse future
  let expandedMonths = $state(new Set());
  $effect(() => {
    const now = new Date();
    const currentKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    const expanded = new Set();
    for (const g of groupedParcelas) {
      if (g.key <= currentKey) expanded.add(g.key);
    }
    // Always expand at least the first group
    if (expanded.size === 0 && groupedParcelas.length > 0) {
      expanded.add(groupedParcelas[0].key);
    }
    expandedMonths = expanded;
  });

  function toggleMonth(key) {
    const next = new Set(expandedMonths);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    expandedMonths = next;
  }

  async function handlePay(parcela) {
    try {
      await financeiro.payParcela(parcela.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function handleCancel(parcela) {
    if (!confirm('Cancelar esta parcela?')) return;
    try {
      await financeiro.cancelParcela(parcela.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function handleCancelLancamento(lancamentoId) {
    if (!confirm('Cancelar este lançamento e todas as parcelas em aberto?')) return;
    try {
      await financeiro.cancelLancamento(lancamentoId);
      invalidateAll();
    } catch (err) {
      alert('Erro ao cancelar: ' + (/** @type {any} */ (err)?.message || 'erro desconhecido'));
    }
  }

  async function handleBulkPay() {
    if (selectedIds.length === 0) return;
    if (!confirm(`Marcar ${selectedIds.length} parcela(s) como paga(s)?`)) return;
    try {
      await financeiro.bulkPayParcelas(selectedIds);
      selectedIds = [];
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  function applyFilters() {
    goto(`/financeiro/pagar?${buildFilterParams()}`);
  }

  function clearFilters() {
    searchInput = '';
    vencimentoFrom = '';
    vencimentoTo = '';
    data.filters.status = '';
    goto('/financeiro/pagar');
  }

  let hasActiveFilters = $derived(!!(data.filters.search || data.filters.status || vencimentoFrom || vencimentoTo));
</script>

<PageHeader title="Contas a Pagar" subtitle="{data.pagination.total} parcela{data.pagination.total !== 1 ? 's' : ''}">
  {#snippet actions()}
    {#if selectedIds.length > 0}
      <Button onclick={handleBulkPay} size="sm">
        <CheckCheck class="mr-1.5 h-4 w-4" />
        Pagar {selectedIds.length}
      </Button>
    {/if}
  {/snippet}
</PageHeader>

<div class="space-y-4 p-4 md:p-6">
  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-2">
    <div class="relative min-w-0 flex-1">
      <Search class="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
      <input
        type="text"
        bind:value={searchInput}
        placeholder="Buscar..."
        class="border-input bg-background h-9 w-full rounded-md border pl-9 pr-3 text-sm"
        onkeydown={(e) => e.key === 'Enter' && applyFilters()}
      />
    </div>
    <select
      value={data.filters.status}
      onchange={(e) => { data.filters.status = e.target.value; applyFilters(); }}
      class="border-input bg-background h-9 rounded-md border px-3 text-sm"
    >
      <option value="">Aberto + Pago</option>
      <option value="ABERTO">Apenas Aberto</option>
      <option value="PAGO">Apenas Pago</option>
      <option value="CANCELADO">Cancelado</option>
      <option value="all">Todos</option>
    </select>
    <input
      type="date"
      bind:value={vencimentoFrom}
      onchange={applyFilters}
      class="border-input bg-background hidden h-9 rounded-md border px-3 text-sm sm:block"
      title="Vencimento de"
    />
    <input
      type="date"
      bind:value={vencimentoTo}
      onchange={applyFilters}
      class="border-input bg-background hidden h-9 rounded-md border px-3 text-sm sm:block"
      title="Vencimento até"
    />
    {#if hasActiveFilters}
      <Button variant="ghost" size="sm" onclick={clearFilters}>
        <X class="mr-1 h-3.5 w-3.5" /> Limpar
      </Button>
    {/if}
  </div>

  <!-- Monthly grouped parcelas -->
  {#if groupedParcelas.length === 0}
    <div class="text-muted-foreground rounded-lg border py-12 text-center text-sm">
      Nenhuma parcela encontrada.
    </div>
  {:else}
    <div class="space-y-3">
      {#each groupedParcelas as group (group.key)}
        <!-- Month header -->
        <div class="rounded-lg border">
          <button
            type="button"
            class="hover:bg-muted/50 flex w-full items-center justify-between px-4 py-3 transition-colors"
            onclick={() => toggleMonth(group.key)}
          >
            <div class="flex items-center gap-3">
              {#if expandedMonths.has(group.key)}
                <ChevronDown class="text-muted-foreground size-4" />
              {:else}
                <ChevronRight class="text-muted-foreground size-4" />
              {/if}
              <span class="font-semibold">{group.label}</span>
              <span class="text-muted-foreground text-sm">
                {group.count} parcela{group.count !== 1 ? 's' : ''}
              </span>
            </div>
            <div class="flex items-center gap-2">
              {#if group.parcelas.some(p => reminderIds.has(p.lancamento))}
                <span class="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                  <Bell class="size-3" /> Lembrete
                </span>
              {/if}
              <span class="font-mono text-sm font-semibold">
                {formatCurrency(group.total, cur)}
              </span>
            </div>
          </button>

          {#if expandedMonths.has(group.key)}
            <div class="border-t">
              <ParcelaTable
                parcelas={group.parcelas}
                currency={cur}
                selectable={true}
                bind:selectedIds
                onpay={handlePay}
                oncancel={handleCancel}
                oncancelLancamento={handleCancelLancamento}
              />
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  <!-- Pagination -->
  {#if data.pagination.totalPages > 1}
    <div class="flex items-center justify-between text-sm">
      <span class="text-muted-foreground">{data.pagination.total} parcela(s)</span>
      <div class="flex gap-1">
        {#each Array.from({ length: Math.min(data.pagination.totalPages, 10) }, (_, i) => i + 1) as pg}
          <Button
            variant={pg === data.pagination.page ? 'default' : 'outline'}
            size="sm"
            class="h-8 w-8"
            onclick={() => goto(`/financeiro/pagar?${buildFilterParams({ page: String(pg) })}`)}
          >
            {pg}
          </Button>
        {/each}
      </div>
    </div>
  {/if}
</div>
