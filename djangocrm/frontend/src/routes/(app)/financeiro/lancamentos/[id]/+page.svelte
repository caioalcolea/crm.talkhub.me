<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { StatusBadge, ParcelaTable } from '$lib/components/financeiro';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { financeiro } from '$lib/api.js';
  import { ArrowLeft, Ban } from '@lucide/svelte';

  let { data } = $props();
  let l = $derived(data.lancamento);
  let loading = $state(false);

  async function handlePayParcela(parcela) {
    try {
      await financeiro.payParcela(parcela.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function handleCancelParcela(parcela) {
    if (!confirm('Cancelar esta parcela?')) return;
    try {
      await financeiro.cancelParcela(parcela.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function handleCancelLancamento() {
    if (!confirm('Cancelar este lançamento e todas as parcelas em aberto?')) return;
    loading = true;
    try {
      await financeiro.cancelLancamento(l.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    } finally {
      loading = false;
    }
  }
</script>

<div class="space-y-6 p-6">
  <!-- Back + Header -->
  <div class="flex items-center gap-3">
    <Button variant="ghost" size="sm" onclick={() => goto('/financeiro/lancamentos')}>
      <ArrowLeft class="mr-1 h-4 w-4" /> Voltar
    </Button>
  </div>

  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold">{l.descricao}</h1>
      <div class="mt-1 flex items-center gap-2">
        <StatusBadge status={l.tipo} />
        <StatusBadge status={l.status} />
      </div>
    </div>
    {#if l.status === 'ABERTO'}
      <Button variant="destructive" size="sm" onclick={handleCancelLancamento} disabled={loading}>
        <Ban class="mr-1 h-4 w-4" />
        Cancelar Lançamento
      </Button>
    {/if}
  </div>

  <!-- Info Grid -->
  <div class="grid grid-cols-2 gap-4 rounded-lg border p-4 md:grid-cols-4">
    <div>
      <span class="text-muted-foreground text-xs font-medium">Valor Total</span>
      <p class="text-lg font-bold">{formatCurrency(l.valor_convertido, 'BRL')}</p>
      {#if l.currency !== 'BRL'}
        <p class="text-muted-foreground text-xs">
          {l.currency_symbol} {parseFloat(l.valor_total).toLocaleString('pt-BR')} ({l.currency})
        </p>
      {/if}
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">Parcelas</span>
      <p class="text-lg font-bold">{l.parcelas_pagas}</p>
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">1° Vencimento</span>
      <p class="font-medium">{formatDate(l.data_primeiro_vencimento)}</p>
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">Forma de Pagamento</span>
      <p class="font-medium">{l.forma_pagamento_nome || '-'}</p>
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">Empresa</span>
      {#if l.account}
        <a href="/accounts/{l.account}" class="text-primary font-medium hover:underline">{l.account_name}</a>
      {:else}
        <p class="font-medium">-</p>
      {/if}
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">Contato</span>
      {#if l.contact}
        <a href="/contacts/{l.contact}" class="text-primary font-medium hover:underline">{l.contact_name}</a>
      {:else}
        <p class="font-medium">-</p>
      {/if}
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">Centro de Custo</span>
      <p class="font-medium">{l.plano_de_contas_nome || '-'}</p>
    </div>
    <div>
      <span class="text-muted-foreground text-xs font-medium">Competência</span>
      <p class="font-medium">{l.competencia_mes}/{l.competencia_ano}</p>
    </div>
  </div>

  {#if l.observacoes}
    <div class="rounded-lg border p-4">
      <span class="text-muted-foreground text-xs font-medium">Observações</span>
      <p class="mt-1 text-sm">{l.observacoes}</p>
    </div>
  {/if}

  <!-- Parcelas -->
  <div>
    <h2 class="mb-3 text-lg font-semibold">Parcelas</h2>
    <ParcelaTable
      parcelas={l.parcelas || []}
      onpay={handlePayParcela}
      oncancel={handleCancelParcela}
    />
  </div>
</div>
