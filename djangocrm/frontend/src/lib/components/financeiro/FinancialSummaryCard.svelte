<script>
  import { DollarSign, TrendingUp, TrendingDown, AlertTriangle, Loader, ExternalLink } from '@lucide/svelte';
  import { financeiro } from '$lib/api.js';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { onMount } from 'svelte';

  /**
   * @type {{
   *   entityId: string,
   *   entityType: 'account' | 'contact' | 'opportunity',
   * }}
   */
  let { entityId, entityType } = $props();

  let report = $state(null);
  let loading = $state(false);
  let error = $state(null);

  let currency = $derived($orgSettings?.default_currency || 'BRL');

  async function loadReport() {
    if (!entityId) return;
    loading = true;
    error = null;
    try {
      report = await financeiro.entityReport(entityId, entityType);
    } catch (e) {
      // 404 = no financial data, 403 = no financial access — both silent
      if (e?.status === 404 || e?.status === 403) {
        report = null;
      } else {
        error = 'Erro ao carregar resumo financeiro';
      }
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadReport();
  });

  // Reload when entity changes
  $effect(() => {
    if (entityId) {
      loadReport();
    }
  });
</script>

{#if loading}
  <div class="flex items-center gap-2 py-4 text-sm text-muted-foreground">
    <Loader class="size-4 animate-spin" />
    Carregando financeiro...
  </div>
{:else if error}
  <div class="flex items-center gap-2 py-2 text-sm text-red-500">
    <AlertTriangle class="size-4" />
    {error}
  </div>
{:else if report && (report.total_receber > 0 || report.total_pagar > 0)}
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h4 class="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        <DollarSign class="size-4" />
        Resumo Financeiro
      </h4>
      <a
        href="/financeiro/lancamentos"
        class="flex items-center gap-1 text-xs text-primary hover:text-primary/80"
      >
        Ver tudo
        <ExternalLink class="size-3" />
      </a>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <!-- A Receber -->
      <div class="rounded-lg border bg-emerald-50 p-2.5 dark:bg-emerald-950/30">
        <div class="flex items-center gap-1 text-[11px] text-muted-foreground">
          <TrendingUp class="size-3 text-emerald-500" />
          A Receber
        </div>
        <div class="text-sm font-bold text-emerald-700 dark:text-emerald-400">
          {formatCurrency(report.total_receber, currency)}
        </div>
      </div>

      <!-- A Pagar -->
      <div class="rounded-lg border bg-rose-50 p-2.5 dark:bg-rose-950/30">
        <div class="flex items-center gap-1 text-[11px] text-muted-foreground">
          <TrendingDown class="size-3 text-rose-500" />
          A Pagar
        </div>
        <div class="text-sm font-bold text-rose-700 dark:text-rose-400">
          {formatCurrency(report.total_pagar, currency)}
        </div>
      </div>

      <!-- Pago -->
      <div class="rounded-lg border p-2.5">
        <div class="text-[11px] text-muted-foreground">Pago</div>
        <div class="text-sm font-bold">{formatCurrency(report.total_pago, currency)}</div>
      </div>

      <!-- Vencido -->
      {#if report.total_vencido > 0}
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-2.5 dark:border-amber-800 dark:bg-amber-950/30">
          <div class="flex items-center gap-1 text-[11px] text-muted-foreground">
            <AlertTriangle class="size-3 text-amber-500" />
            Vencido
          </div>
          <div class="text-sm font-bold text-amber-700 dark:text-amber-400">
            {formatCurrency(report.total_vencido, currency)}
          </div>
        </div>
      {:else}
        <!-- Saldo -->
        <div class="rounded-lg border p-2.5">
          <div class="text-[11px] text-muted-foreground">Saldo</div>
          <div class="text-sm font-bold {report.saldo >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">
            {formatCurrency(report.saldo, currency)}
          </div>
        </div>
      {/if}
    </div>

    <!-- Recent lancamentos -->
    {#if report.lancamentos?.length > 0}
      <div class="space-y-1">
        <p class="text-[11px] font-medium text-muted-foreground">Últimos lançamentos</p>
        {#each report.lancamentos.slice(0, 3) as lanc (lanc.id)}
          <a
            href="/financeiro/lancamentos/{lanc.id}"
            class="flex items-center justify-between rounded-md px-2 py-1.5 text-xs hover:bg-accent"
          >
            <div class="flex items-center gap-2">
              <span class="inline-block size-1.5 rounded-full {lanc.tipo === 'RECEBER' ? 'bg-emerald-500' : 'bg-rose-500'}"></span>
              <span class="max-w-[160px] truncate">{lanc.descricao}</span>
            </div>
            <span class="font-medium">{formatCurrency(lanc.valor_total, lanc.currency || currency)}</span>
          </a>
        {/each}
      </div>
    {/if}
  </div>
{/if}
