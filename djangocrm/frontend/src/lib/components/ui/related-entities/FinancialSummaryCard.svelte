<script>
  import { DollarSign, AlertTriangle } from '@lucide/svelte';
  import { formatCurrency } from '$lib/utils/formatting.js';

  /**
   * @type {{
   *   financial: { total_receber?: number, total_pagar?: number, total_aberto?: number, total_vencido?: number },
   *   currency?: string
   * }}
   */
  let { financial, currency = 'BRL' } = $props();
</script>

<div class="rounded-lg border bg-card p-3 space-y-2">
  <div class="flex items-center gap-2 text-sm font-medium">
    <DollarSign class="size-4 text-emerald-600" />
    <span>Financeiro</span>
  </div>
  <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
    <div class="text-muted-foreground">A receber</div>
    <div class="text-right font-medium text-emerald-600">
      {formatCurrency(financial.total_receber, currency)}
    </div>
    {#if financial.total_pagar !== undefined}
      <div class="text-muted-foreground">A pagar</div>
      <div class="text-right font-medium text-red-500">
        {formatCurrency(financial.total_pagar, currency)}
      </div>
    {/if}
    <div class="text-muted-foreground">Em aberto</div>
    <div class="text-right font-medium">
      {formatCurrency(financial.total_aberto, currency)}
    </div>
    {#if financial.total_vencido > 0}
      <div class="flex items-center gap-1 text-muted-foreground">
        <AlertTriangle class="size-3 text-amber-500" />
        Vencido
      </div>
      <div class="text-right font-medium text-amber-600">
        {formatCurrency(financial.total_vencido, currency)}
      </div>
    {/if}
  </div>
</div>
