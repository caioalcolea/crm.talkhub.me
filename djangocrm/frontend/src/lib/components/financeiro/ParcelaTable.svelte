<script>
  import StatusBadge from './StatusBadge.svelte';
  import { Button } from '$lib/components/ui/button/index.js';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { Check, X } from '@lucide/svelte';

  let {
    parcelas = [],
    currency = 'BRL',
    onpay,
    oncancel,
    selectable = false,
    selectedIds = $bindable([])
  } = $props();

  function toggleSelect(id) {
    if (selectedIds.includes(id)) {
      selectedIds = selectedIds.filter((i) => i !== id);
    } else {
      selectedIds = [...selectedIds, id];
    }
  }

  function toggleAll() {
    const openIds = parcelas.filter((p) => p.status === 'ABERTO').map((p) => p.id);
    if (selectedIds.length === openIds.length) {
      selectedIds = [];
    } else {
      selectedIds = openIds;
    }
  }
</script>

<div class="overflow-x-auto rounded-lg border">
  <table class="w-full text-sm">
    <thead>
      <tr class="bg-muted/50 border-b">
        {#if selectable}
          <th class="w-10 px-3 py-2">
            <input
              type="checkbox"
              checked={selectedIds.length > 0 && selectedIds.length === parcelas.filter((p) => p.status === 'ABERTO').length}
              onchange={toggleAll}
              class="rounded"
            />
          </th>
        {/if}
        <th class="px-3 py-2 text-left font-medium">Parcela</th>
        <th class="px-3 py-2 text-left font-medium">Descrição</th>
        <th class="hidden px-3 py-2 text-left font-medium md:table-cell">Pessoa</th>
        <th class="px-3 py-2 text-right font-medium">Valor</th>
        <th class="px-3 py-2 text-left font-medium">Vencimento</th>
        <th class="hidden px-3 py-2 text-left font-medium lg:table-cell">Pagamento</th>
        <th class="px-3 py-2 text-left font-medium">Status</th>
        <th class="hidden px-3 py-2 text-left font-medium md:table-cell">Info</th>
        <th class="px-3 py-2 text-right font-medium">Ações</th>
      </tr>
    </thead>
    <tbody>
      {#each parcelas as parcela (parcela.id)}
        <tr class="hover:bg-muted/30 border-b transition-colors">
          {#if selectable}
            <td class="px-3 py-2">
              {#if parcela.status === 'ABERTO'}
                <input
                  type="checkbox"
                  checked={selectedIds.includes(parcela.id)}
                  onchange={() => toggleSelect(parcela.id)}
                  class="rounded"
                />
              {/if}
            </td>
          {/if}
          <td class="px-3 py-2 font-medium">
            {parcela.numero}/{parcela.total_parcelas || parcela.totalParcelas || '?'}
          </td>
          <td class="max-w-[200px] truncate px-3 py-2">
            {parcela.lancamento_descricao || parcela.lancamentoDescricao || '-'}
          </td>
          <td class="hidden px-3 py-2 text-xs md:table-cell">
            {parcela.account_name || parcela.accountName || parcela.contact_name || parcela.contactName || '-'}
          </td>
          <td class="px-3 py-2 text-right font-mono text-xs">
            {formatCurrency(parcela.valor_parcela_convertido || parcela.valorParcelaConvertido, currency)}
          </td>
          <td class="px-3 py-2 text-xs">
            {formatDate(parcela.data_vencimento || parcela.dataVencimento)}
          </td>
          <td class="hidden px-3 py-2 text-xs lg:table-cell">
            {formatDate(parcela.data_pagamento || parcela.dataPagamento) || '-'}
          </td>
          <td class="px-3 py-2">
            <StatusBadge status={parcela.status} />
          </td>
          <td class="hidden px-3 py-2 text-xs md:table-cell">
            {#if parcela.dias_atraso > 0 || parcela.diasAtraso > 0}
              <span class="text-destructive font-medium">
                {parcela.status_message || parcela.statusMessage || `${parcela.dias_atraso || parcela.diasAtraso}d atraso`}
              </span>
            {:else}
              <span class="text-muted-foreground">{parcela.status_message || parcela.statusMessage || ''}</span>
            {/if}
          </td>
          <td class="px-3 py-2 text-right">
            {#if parcela.status === 'ABERTO'}
              <div class="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-7 px-2 text-emerald-600"
                  onclick={() => onpay?.(parcela)}
                  title="Marcar como Pago"
                >
                  <Check class="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="text-destructive h-7 px-2"
                  onclick={() => oncancel?.(parcela)}
                  title="Cancelar"
                >
                  <X class="h-3.5 w-3.5" />
                </Button>
              </div>
            {/if}
          </td>
        </tr>
      {:else}
        <tr>
          <td colspan={selectable ? 10 : 9} class="text-muted-foreground px-3 py-8 text-center">
            Nenhuma parcela encontrada.
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
