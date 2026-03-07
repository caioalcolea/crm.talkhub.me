<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/stores';
  import { Button } from '$lib/components/ui/button/index.js';
  import { StatusBadge, TransactionForm } from '$lib/components/financeiro';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { Plus, Search, X } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { financeiro } from '$lib/api.js';

  let { data } = $props();

  let showCreateModal = $state(false);
  let loading = $state(false);
  let searchInput = $state('');

  $effect(() => {
    if (data?.filters?.search) searchInput = data.filters.search;
  });

  let formData = $state({
    tipo: 'RECEBER',
    descricao: '',
    observacoes: '',
    plano_de_contas: '',
    account: '',
    contact: '',
    opportunity: '',
    invoice: '',
    currency: 'BRL',
    valor_total: '',
    exchange_rate_to_base: '1',
    forma_pagamento: '',
    numero_parcelas: 1,
    data_primeiro_vencimento: ''
  });

  function resetForm() {
    formData = {
      tipo: 'RECEBER',
      descricao: '',
      observacoes: '',
      plano_de_contas: '',
      account: '',
      contact: '',
      opportunity: '',
      invoice: '',
      currency: 'BRL',
      valor_total: '',
      exchange_rate_to_base: '1',
      forma_pagamento: '',
      numero_parcelas: 1,
      data_primeiro_vencimento: ''
    };
  }

  async function handleCreate(fd) {
    loading = true;
    try {
      await financeiro.lancamentos.create({
        ...fd,
        plano_de_contas: fd.plano_de_contas || null,
        account: fd.account || null,
        contact: fd.contact || null,
        opportunity: fd.opportunity || null,
        invoice: fd.invoice || null,
        forma_pagamento: fd.forma_pagamento || null
      });
      showCreateModal = false;
      resetForm();
      invalidateAll();
    } catch (err) {
      alert('Erro ao criar: ' + err.message);
    } finally {
      loading = false;
    }
  }

  function applyFilters() {
    const params = new URLSearchParams();
    if (searchInput) params.set('search', searchInput);
    const tipo = data.filters.tipo;
    if (tipo) params.set('tipo', tipo);
    const status = data.filters.status;
    if (status) params.set('status', status);
    goto(`/financeiro/lancamentos?${params.toString()}`);
  }

  function clearFilters() {
    searchInput = '';
    goto('/financeiro/lancamentos');
  }
</script>

<div class="space-y-4 p-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Lançamentos</h1>
      <p class="text-muted-foreground text-sm">Gerencie contas a pagar e receber</p>
    </div>
    <Button onclick={() => { resetForm(); showCreateModal = true; }}>
      <Plus class="mr-1.5 h-4 w-4" />
      Novo Lançamento
    </Button>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-2">
    <div class="relative flex-1">
      <Search class="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
      <input
        type="text"
        bind:value={searchInput}
        placeholder="Buscar por descrição..."
        class="border-input bg-background h-9 w-full rounded-md border pl-9 pr-3 text-sm"
        onkeydown={(e) => e.key === 'Enter' && applyFilters()}
      />
    </div>
    <select
      value={data.filters.tipo}
      onchange={(e) => { data.filters.tipo = e.target.value; applyFilters(); }}
      class="border-input bg-background h-9 rounded-md border px-3 text-sm"
    >
      <option value="">Todos os tipos</option>
      <option value="PAGAR">Pagar</option>
      <option value="RECEBER">Receber</option>
    </select>
    <select
      value={data.filters.status}
      onchange={(e) => { data.filters.status = e.target.value; applyFilters(); }}
      class="border-input bg-background h-9 rounded-md border px-3 text-sm"
    >
      <option value="">Todos os status</option>
      <option value="ABERTO">Aberto</option>
      <option value="PAGO">Pago</option>
      <option value="CANCELADO">Cancelado</option>
    </select>
    {#if data.filters.search || data.filters.tipo || data.filters.status}
      <Button variant="ghost" size="sm" onclick={clearFilters}>
        <X class="mr-1 h-3.5 w-3.5" /> Limpar
      </Button>
    {/if}
  </div>

  <!-- Table -->
  <div class="overflow-x-auto rounded-lg border">
    <table class="w-full text-sm">
      <thead>
        <tr class="bg-muted/50 border-b">
          <th class="px-3 py-2.5 text-left font-medium">Descrição</th>
          <th class="px-3 py-2.5 text-left font-medium">Tipo</th>
          <th class="px-3 py-2.5 text-left font-medium">Pessoa</th>
          <th class="px-3 py-2.5 text-left font-medium">Plano</th>
          <th class="px-3 py-2.5 text-right font-medium">Valor</th>
          <th class="px-3 py-2.5 text-left font-medium">Parcelas</th>
          <th class="px-3 py-2.5 text-left font-medium">Status</th>
          <th class="px-3 py-2.5 text-left font-medium">Vencimento</th>
        </tr>
      </thead>
      <tbody>
        {#each data.lancamentos as item (item.id)}
          <tr
            class="hover:bg-muted/30 cursor-pointer border-b transition-colors"
            onclick={() => goto(`/financeiro/lancamentos/${item.id}`)}
          >
            <td class="max-w-[220px] truncate px-3 py-2.5 font-medium">{item.descricao}</td>
            <td class="px-3 py-2.5"><StatusBadge status={item.tipo} /></td>
            <td class="px-3 py-2.5 text-xs">{item.account_name || item.contact_name || '-'}</td>
            <td class="max-w-[150px] truncate px-3 py-2.5 text-xs">{item.plano_de_contas_nome || '-'}</td>
            <td class="px-3 py-2.5 text-right font-mono text-xs">
              {#if item.currency_symbol}
                <span class="text-muted-foreground mr-1 text-[10px]">{item.currency_symbol}</span>
              {/if}
              {formatCurrency(item.valor_convertido, 'BRL')}
            </td>
            <td class="px-3 py-2.5 text-xs">{item.parcelas_pagas}</td>
            <td class="px-3 py-2.5"><StatusBadge status={item.status} /></td>
            <td class="px-3 py-2.5 text-xs">{formatDate(item.data_primeiro_vencimento)}</td>
          </tr>
        {:else}
          <tr>
            <td colspan="8" class="text-muted-foreground px-3 py-12 text-center">
              Nenhum lançamento encontrado.
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <!-- Pagination -->
  {#if data.pagination.totalPages > 1}
    <div class="flex items-center justify-between text-sm">
      <span class="text-muted-foreground">
        {data.pagination.total} lançamento{data.pagination.total !== 1 ? 's' : ''}
      </span>
      <div class="flex gap-1">
        {#each Array.from({ length: Math.min(data.pagination.totalPages, 10) }, (_, i) => i + 1) as pg}
          <Button
            variant={pg === data.pagination.page ? 'default' : 'outline'}
            size="sm"
            class="h-8 w-8"
            onclick={() => goto(`/financeiro/lancamentos?page=${pg}`)}
          >
            {pg}
          </Button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<!-- Create Modal -->
<Dialog.Root bind:open={showCreateModal}>
  <Dialog.Content class="max-w-2xl">
    <Dialog.Header>
      <Dialog.Title>Novo Lançamento</Dialog.Title>
      <Dialog.Description>Crie um novo lançamento financeiro.</Dialog.Description>
    </Dialog.Header>
    <TransactionForm
      bind:formData
      formOptions={data.formOptions}
      mode="create"
      {loading}
      onsubmit={handleCreate}
      oncancel={() => (showCreateModal = false)}
    />
  </Dialog.Content>
</Dialog.Root>
