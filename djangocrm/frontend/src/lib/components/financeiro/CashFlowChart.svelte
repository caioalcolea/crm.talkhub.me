<script>
  import { formatCurrency } from '$lib/utils/formatting.js';

  let { data = [], currency = 'BRL' } = $props();

  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  const maxValue = $derived(
    Math.max(...data.map((d) => Math.max(d.receber || 0, d.pagar || 0)), 1)
  );
</script>

<div class="space-y-3">
  <div class="flex items-center gap-4 text-xs">
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-emerald-500"></span>
      Recebido
    </span>
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-rose-500"></span>
      Pago
    </span>
  </div>

  <div class="flex items-end gap-1" style="height: 200px;">
    {#each data as item, i}
      {@const receberH = maxValue > 0 ? (item.receber / maxValue) * 100 : 0}
      {@const pagarH = maxValue > 0 ? (item.pagar / maxValue) * 100 : 0}
      <div class="flex flex-1 flex-col items-center gap-0.5">
        <div class="flex w-full items-end justify-center gap-0.5" style="height: 180px;">
          <div
            class="w-[40%] rounded-t bg-emerald-500 transition-all"
            style="height: {receberH}%"
            title="Recebido: {formatCurrency(item.receber, currency)}"
          ></div>
          <div
            class="w-[40%] rounded-t bg-rose-500 transition-all"
            style="height: {pagarH}%"
            title="Pago: {formatCurrency(item.pagar, currency)}"
          ></div>
        </div>
        <span class="text-muted-foreground text-[10px]">{months[i] || i + 1}</span>
      </div>
    {/each}
  </div>
</div>
