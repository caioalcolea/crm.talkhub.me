<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { StatusBadge, ParcelaTable, TransactionForm } from '$lib/components/financeiro';
  import { PageHeader } from '$lib/components/layout';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { financeiro, getCurrentUser } from '$lib/api.js';
  import { orgSettings } from '$lib/stores/org.js';
  import ReminderSection from '$lib/components/assistant/ReminderSection.svelte';
  import EntityRunsHistory from '$lib/components/assistant/EntityRunsHistory.svelte';
  import { ArrowLeft, Ban, Pencil, Repeat, Square, Trash2 } from '@lucide/svelte';

  let { data } = $props();
  let l = $derived(data.lancamento);
  let orgCurrency = $derived($orgSettings.default_currency || 'BRL');
  let loading = $state(false);
  let editing = $state(false);

  let isAdmin = $derived.by(() => {
    const user = getCurrentUser();
    return user?.organizations?.some((/** @type {any} */ o) => o.role === 'ADMIN') ?? false;
  });

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
      for (const key of ['plano_de_contas', 'account', 'contact', 'opportunity', 'invoice', 'forma_pagamento', 'product']) {
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

  async function handleDeleteLancamento() {
    if (!confirm(`Excluir permanentemente "${l.descricao}"? Esta ação não pode ser desfeita.`)) return;
    loading = true;
    try {
      await financeiro.deleteLancamento(l.id);
      goto('/financeiro/lancamentos');
    } catch (err) {
      alert('Erro ao excluir: ' + (/** @type {any} */ (err)?.message || 'erro desconhecido'));
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

<PageHeader title={editing ? 'Editar Lancamento' : l.descricao}>
  {#snippet actions()}
    {#if !editing}
      <Button variant="ghost" size="sm" onclick={() => goto('/financeiro/lancamentos')}>
        <ArrowLeft class="mr-1 h-4 w-4" /><span class="hidden sm:inline">Voltar</span>
      </Button>
      {#if l.status !== 'CANCELADO'}
        <Button variant="outline" size="sm" onclick={startEdit}>
          <Pencil class="mr-1 h-4 w-4" /><span class="hidden sm:inline">Editar</span>
        </Button>
      {/if}
      {#if l.is_recorrente && l.status === 'ABERTO'}
        <Button variant="outline" size="sm" onclick={handleToggleRecorrencia} disabled={loading}>
          {#if l.recorrencia_ativa}
            <Square class="mr-1 h-4 w-4" /><span class="hidden sm:inline">Parar Recorrencia</span>
          {:else}
            <Repeat class="mr-1 h-4 w-4" /><span class="hidden sm:inline">Reativar</span>
          {/if}
        </Button>
      {/if}
      {#if l.status === 'ABERTO'}
        <Button variant="destructive" size="sm" onclick={handleCancelLancamento} disabled={loading}>
          <Ban class="mr-1 h-4 w-4" /><span class="hidden sm:inline">Cancelar</span>
        </Button>
      {/if}
      {#if l.status === 'CANCELADO' && isAdmin}
        <Button variant="destructive" size="sm" onclick={handleDeleteLancamento} disabled={loading}>
          <Trash2 class="mr-1 h-4 w-4" /><span class="hidden sm:inline">Excluir</span>
        </Button>
      {/if}
    {/if}
  {/snippet}
</PageHeader>

<div class="space-y-6 p-4 md:p-6">
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
    <div class="flex flex-wrap items-center gap-2">
      <StatusBadge status={l.tipo} />
      <StatusBadge status={l.status} tipo={l.tipo} />
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

    <!-- Info Grid -->
    <div class="grid grid-cols-1 gap-4 rounded-lg border p-4 sm:grid-cols-2 md:grid-cols-4">
      <div>
        <span class="text-muted-foreground text-xs font-medium">
          {#if l.is_recorrente}Valor por Período{:else}Valor Total{/if}
        </span>
        <p class="text-lg font-bold">{formatCurrency(l.valor_convertido, orgCurrency)}</p>
        {#if l.is_recorrente}
          <p class="text-muted-foreground text-xs">
            por período ({l.recorrencia_label || l.recorrencia_tipo || 'recorrente'})
          </p>
        {:else if l.numero_parcelas > 1}
          <p class="text-muted-foreground text-xs">
            em {l.numero_parcelas} parcelas de {formatCurrency(l.valor_parcela_display, orgCurrency)}
          </p>
        {/if}
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

    <!-- Audit Trail -->
    {#if l.created_by_name || l.updated_by_name || l.cancelled_by_name}
      <div class="text-muted-foreground space-y-0.5 text-xs">
        {#if l.created_by_name}
          <p>Criado por <span class="font-medium">{l.created_by_name}</span> em {formatDate(l.created_at)}</p>
        {/if}
        {#if l.updated_by_name && l.updated_at !== l.created_at}
          <p>Atualizado por <span class="font-medium">{l.updated_by_name}</span> em {formatDate(l.updated_at)}</p>
        {/if}
        {#if l.cancelled_by_name}
          <p class="text-destructive">Cancelado por <span class="font-medium">{l.cancelled_by_name}</span> em {formatDate(l.cancelled_at)}</p>
        {/if}
      </div>
    {/if}

    <!-- Parcelas -->
    <div>
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-lg font-semibold">Parcelas</h2>
        {#if l.is_recorrente && l.parcelas?.length > 0}
          {@const totalGerado = l.parcelas.reduce((sum, p) => sum + parseFloat(p.valor_parcela_convertido || 0), 0)}
          <span class="text-muted-foreground text-sm">
            Total gerado: <span class="font-medium">{formatCurrency(totalGerado, orgCurrency)}</span>
            ({l.parcelas.length} parcelas)
          </span>
        {/if}
      </div>
      <ParcelaTable
        parcelas={l.parcelas || []}
        onpay={handlePayParcela}
        oncancel={handleCancelParcela}
      />
    </div>

    <!-- Reminders -->
    {#if l.status !== 'CANCELADO'}
      <ReminderSection
        lancamentoId={l.id}
        reminders={data.reminders || []}
        tipo={l.tipo}
      />
      <div class="mt-4">
        <EntityRunsHistory targetType="financeiro.lancamento" targetId={l.id} />
      </div>
    {/if}
  {/if}
</div>
