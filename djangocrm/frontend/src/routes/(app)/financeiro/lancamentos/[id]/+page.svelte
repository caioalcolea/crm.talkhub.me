<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { StatusBadge, ParcelaTable, TransactionForm } from '$lib/components/financeiro';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { financeiro } from '$lib/api.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { ArrowLeft, Ban, Pencil, Repeat, Square } from '@lucide/svelte';

  let { data } = $props();
  let l = $derived(data.lancamento);
  let orgCurrency = $derived($orgSettings.default_currency || 'BRL');
  let loading = $state(false);
  let editing = $state(false);

  let editFormData = $state({});

  function startEdit() {
    editFormData = {
      descricao: l.descricao || '',
      observacoes: l.observacoes || '',
      plano_de_contas: l.plano_de_contas || '',
      account: l.account || '',
      contact: l.contact || '',
      opportunity: l.opportunity || '',
      invoice: l.invoice || '',
      forma_pagamento: l.forma_pagamento || '',
      currency: l.currency || orgCurrency,
      valor_total: l.valor_total || '',
      exchange_rate_to_base: l.exchange_rate_to_base || '1',
      exchange_rate_type: l.exchange_rate_type || 'FIXO',
      numero_parcelas: l.numero_parcelas || 1,
      data_primeiro_vencimento: l.data_primeiro_vencimento || '',
      is_recorrente: l.is_recorrente || false,
      recorrencia_tipo: l.recorrencia_tipo || '',
      data_fim_recorrencia: l.data_fim_recorrencia || '',
      recorrencia_ativa: l.recorrencia_ativa !== false,
    };
    editing = true;
  }

  async function handleSaveEdit(fd) {
    loading = true;
    try {
      const body = { ...fd };
      // Clean empty strings to null for FK fields
      for (const key of ['plano_de_contas', 'account', 'contact', 'opportunity', 'invoice', 'forma_pagamento']) {
        if (body[key] === '') body[key] = null;
      }
      if (body.data_fim_recorrencia === '') body.data_fim_recorrencia = null;
      if (body.recorrencia_tipo === '') body.recorrencia_tipo = null;

      await financeiro.lancamentos.patch(l.id, body);
      editing = false;
      invalidateAll();
    } catch (err) {
      alert('Erro ao salvar: ' + err.message);
    } finally {
      loading = false;
    }
  }

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
    if (!confirm('Cancelar este lancamento e todas as parcelas em aberto?')) return;
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

  async function handleToggleRecorrencia() {
    const newVal = !l.recorrencia_ativa;
    const msg = newVal
      ? 'Reativar a recorrencia deste lancamento?'
      : 'Parar a recorrencia deste lancamento? Parcelas ja geradas serao mantidas.';
    if (!confirm(msg)) return;
    loading = true;
    try {
      await financeiro.lancamentos.patch(l.id, { recorrencia_ativa: newVal });
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

  {#if editing}
    <!-- Edit Mode -->
    <div class="rounded-lg border p-4">
      <h2 class="mb-4 text-lg font-semibold">Editar Lancamento</h2>
      <TransactionForm
        bind:formData={editFormData}
        formOptions={data.formOptions}
        mode="edit"
        canEditFinancials={l.can_edit_financials}
        {loading}
        onsubmit={handleSaveEdit}
        oncancel={() => (editing = false)}
      />
    </div>
  {:else}
    <!-- View Mode -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold">{l.descricao}</h1>
        <div class="mt-1 flex items-center gap-2">
          <StatusBadge status={l.tipo} />
          <StatusBadge status={l.status} />
          {#if l.is_recorrente}
            <span class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
              <Repeat class="mr-1 h-3 w-3" />
              {l.recorrencia_tipo || 'Recorrente'}
              {#if !l.recorrencia_ativa}
                <span class="ml-1 text-gray-500">(parado)</span>
              {/if}
            </span>
          {/if}
          {#if l.exchange_rate_type === 'VARIAVEL'}
            <span class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
              Taxa variavel
            </span>
          {/if}
        </div>
      </div>
      <div class="flex items-center gap-2">
        {#if l.status !== 'CANCELADO'}
          <Button variant="outline" size="sm" onclick={startEdit}>
            <Pencil class="mr-1 h-4 w-4" />
            Editar
          </Button>
        {/if}
        {#if l.is_recorrente && l.status === 'ABERTO'}
          <Button
            variant="outline"
            size="sm"
            onclick={handleToggleRecorrencia}
            disabled={loading}
          >
            {#if l.recorrencia_ativa}
              <Square class="mr-1 h-4 w-4" /> Parar Recorrencia
            {:else}
              <Repeat class="mr-1 h-4 w-4" /> Reativar
            {/if}
          </Button>
        {/if}
        {#if l.status === 'ABERTO'}
          <Button variant="destructive" size="sm" onclick={handleCancelLancamento} disabled={loading}>
            <Ban class="mr-1 h-4 w-4" />
            Cancelar
          </Button>
        {/if}
      </div>
    </div>

    <!-- Info Grid -->
    <div class="grid grid-cols-2 gap-4 rounded-lg border p-4 md:grid-cols-4">
      <div>
        <span class="text-muted-foreground text-xs font-medium">Valor Total</span>
        <p class="text-lg font-bold">{formatCurrency(l.valor_convertido, orgCurrency)}</p>
        {#if l.currency !== orgCurrency}
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
        <span class="text-muted-foreground text-xs font-medium">Competencia</span>
        <p class="font-medium">{l.competencia_mes}/{l.competencia_ano}</p>
      </div>
      {#if l.data_fim_recorrencia}
        <div>
          <span class="text-muted-foreground text-xs font-medium">Fim da Recorrencia</span>
          <p class="font-medium">{formatDate(l.data_fim_recorrencia)}</p>
        </div>
      {/if}
    </div>

    {#if l.observacoes}
      <div class="rounded-lg border p-4">
        <span class="text-muted-foreground text-xs font-medium">Observacoes</span>
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
  {/if}
</div>
