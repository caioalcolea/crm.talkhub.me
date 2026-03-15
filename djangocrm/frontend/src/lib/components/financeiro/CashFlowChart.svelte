<script>
  import { formatCurrency } from '$lib/utils/formatting.js';

  let { data = [], currency = 'BRL' } = $props();

  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  const currentMonth = new Date().getMonth() + 1;

  const maxValue = $derived(
    Math.max(
      ...data.map((d) => Math.max(
        (d.receber || 0) + (d.receber_projetado || 0),
        (d.pagar || 0) + (d.pagar_projetado || 0)
      )),
      1
    )
  );
</script>

<div class="space-y-3">
  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-emerald-500"></span>
      Recebido
    </span>
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-rose-500"></span>
      Pago
    </span>
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-emerald-500/40"></span>
      Previsto Receber
    </span>
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-3 w-3 rounded-sm bg-rose-500/40"></span>
      Previsto Pagar
    </span>
  </div>

  <div class="flex items-end gap-1" style="height: 200px;">
    {#each data as item, i}
      {@const receberTotal = (item.receber || 0) + (item.receber_projetado || 0)}
      {@const pagarTotal = (item.pagar || 0) + (item.pagar_projetado || 0)}
      {@const receberTotalH = maxValue > 0 ? (receberTotal / maxValue) * 100 : 0}
      {@const pagarTotalH = maxValue > 0 ? (pagarTotal / maxValue) * 100 : 0}
      {@const receberRealPct = receberTotal > 0 ? ((item.receber || 0) / receberTotal) * 100 : 0}
      {@const pagarRealPct = pagarTotal > 0 ? ((item.pagar || 0) / pagarTotal) * 100 : 0}
      {@const isCurrentMonth = item.mes === currentMonth}
      <div class="flex flex-1 flex-col items-center gap-0.5">
        <div class="flex w-full items-end justify-center gap-0.5" style="height: 180px;">
          <!-- Receber bar (stacked: solid bottom + faded top) -->
          <div
            class="flex w-[40%] flex-col justify-end overflow-hidden rounded-t"
            style="height: {receberTotalH}%"
            title="Recebido: {formatCurrency(item.receber || 0, currency)} | Previsto: {formatCurrency(item.receber_projetado || 0, currency)}"
          >
            <div class="bg-emerald-500/40" style="flex: {100 - receberRealPct}"></div>
            <div class="bg-emerald-500" style="flex: {receberRealPct}"></div>
          </div>
          <!-- Pagar bar (stacked: solid bottom + faded top) -->
          <div
            class="flex w-[40%] flex-col justify-end overflow-hidden rounded-t"
            style="height: {pagarTotalH}%"
            title="Pago: {formatCurrency(item.pagar || 0, currency)} | Previsto: {formatCurrency(item.pagar_projetado || 0, currency)}"
          >
            <div class="bg-rose-500/40" style="flex: {100 - pagarRealPct}"></div>
            <div class="bg-rose-500" style="flex: {pagarRealPct}"></div>
          </div>
        </div>
        <span class="text-[10px] {isCurrentMonth ? 'font-bold text-foreground' : 'text-muted-foreground'}">{months[i] || i + 1}</span>
      </div>
    {/each}
  </div>
</div>
