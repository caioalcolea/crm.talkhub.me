<script>
  import { page } from '$app/stores';
  import { goto, invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import { tick } from 'svelte';
  import { toast } from 'svelte-sonner';

  import { PageHeader } from '$lib/components/layout';
  import { Button } from '$lib/components/ui/button';
  import { FilterBar, SearchInput, SelectFilter } from '$lib/components/ui/filter';
  import { Pagination } from '$lib/components/ui/pagination';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { ShoppingCart, Plus, ArrowLeft, Filter, Zap, Trash2 } from '@lucide/svelte';

  /** @type {{ data: import('./$types').PageData }} */
  let { data } = $props();

  const STATUS_OPTIONS = [
    { value: 'DRAFT', label: 'Rascunho' },
    { value: 'ACTIVATED', label: 'Ativado' },
    { value: 'COMPLETED', label: 'Concluído' },
    { value: 'CANCELLED', label: 'Cancelado' }
  ];

  const orders = $derived(data.orders);
  const pagination = $derived(data.pagination);
  const filters = $derived(data.filters);
  const accounts = $derived(data.accounts || []);

  let filtersExpanded = $state(false);
  let showCreateDialog = $state(false);

  // Create form state
  let createFormState = $state({
    name: '',
    account: '',
    currency: 'BRL',
    order_date: new Date().toISOString().split('T')[0],
    total_amount: '0',
    description: ''
  });

  let createForm;
  let activateForm;
  let deleteForm;
  let actionOrderId = $state('');

  const activeFiltersCount = $derived(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.status) count++;
    return count;
  });

  async function updateFilters(newFilters) {
    const url = new URL($page.url);
    ['search', 'status'].forEach((key) => url.searchParams.delete(key));
    Object.entries(newFilters).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
    });
    url.searchParams.set('page', '1');
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  async function clearFilters() {
    await updateFilters({});
  }

  async function handlePageChange(newPage) {
    const url = new URL($page.url);
    url.searchParams.set('page', newPage.toString());
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  async function handleLimitChange(newLimit) {
    const url = new URL($page.url);
    url.searchParams.set('limit', newLimit.toString());
    url.searchParams.set('page', '1');
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  async function handleCreate() {
    await tick();
    createForm.requestSubmit();
  }

  async function handleActivate(orderId) {
    if (!confirm('Ativar este pedido? Isso criará o lançamento no financeiro e atualizará o estoque.')) return;
    actionOrderId = orderId;
    await tick();
    activateForm.requestSubmit();
  }

  async function handleDelete(orderId) {
    if (!confirm('Excluir este pedido?')) return;
    actionOrderId = orderId;
    await tick();
    deleteForm.requestSubmit();
  }

  function getStatusBadge(status) {
    const map = {
      DRAFT: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      ACTIVATED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      COMPLETED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
      CANCELLED: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
    };
    return map[status] || map.DRAFT;
  }

  function getStatusLabel(status) {
    const map = { DRAFT: 'Rascunho', ACTIVATED: 'Ativado', COMPLETED: 'Concluído', CANCELLED: 'Cancelado' };
    return map[status] || status;
  }
</script>

<!-- Hidden forms -->
<form
  bind:this={createForm}
  method="POST"
  action="?/create"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'success') {
        toast.success('Pedido de compra criado');
        showCreateDialog = false;
        createFormState = { name: '', account: '', currency: 'BRL', order_date: new Date().toISOString().split('T')[0], total_amount: '0', description: '' };
        invalidateAll();
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao criar pedido');
      }
    };
  }}
>
  <input type="hidden" name="name" value={createFormState.name} />
  <input type="hidden" name="account" value={createFormState.account} />
  <input type="hidden" name="currency" value={createFormState.currency} />
  <input type="hidden" name="order_date" value={createFormState.order_date} />
  <input type="hidden" name="total_amount" value={createFormState.total_amount} />
  <input type="hidden" name="description" value={createFormState.description} />
</form>

<form
  bind:this={activateForm}
  method="POST"
  action="?/activate"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'success') {
        toast.success('Pedido ativado — financeiro e estoque atualizados');
        invalidateAll();
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao ativar');
      }
    };
  }}
>
  <input type="hidden" name="orderId" value={actionOrderId} />
</form>

<form
  bind:this={deleteForm}
  method="POST"
  action="?/delete"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'success') {
        toast.success('Pedido excluído');
        invalidateAll();
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao excluir');
      }
    };
  }}
>
  <input type="hidden" name="orderId" value={actionOrderId} />
</form>

<div class="flex flex-col gap-4 p-6">
  <PageHeader title="Pedidos de Compra">
    {#snippet actions()}
      <Button variant="ghost" size="sm" onclick={() => goto('/invoices')}>
        <ArrowLeft class="mr-2 size-4" />
        Faturamento
      </Button>

      <Button
        variant="outline"
        size="sm"
        onclick={() => (filtersExpanded = !filtersExpanded)}
        class="gap-2"
      >
        <Filter class="size-4" />
        Filtros
        {#if activeFiltersCount() > 0}
          <span class="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
            {activeFiltersCount()}
          </span>
        {/if}
      </Button>

      <Button onclick={() => (showCreateDialog = true)} class="gap-2">
        <Plus class="size-4" />
        Novo Pedido
      </Button>
    {/snippet}
  </PageHeader>

  <FilterBar
    minimal
    expanded={filtersExpanded}
    activeCount={activeFiltersCount()}
    onClear={clearFilters}
  >
    <SearchInput
      value={filters.search}
      placeholder="Buscar pedidos..."
      onchange={(value) => updateFilters({ ...filters, search: value })}
    />
    <SelectFilter
      label="Status"
      value={filters.status}
      options={STATUS_OPTIONS}
      onchange={(value) => updateFilters({ ...filters, status: value })}
    />
  </FilterBar>

  <!-- Orders Table -->
  {#if orders.length > 0}
    <div class="overflow-x-auto rounded-lg border border-border bg-background">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border bg-muted/50">
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Pedido</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Fornecedor</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Data</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Total</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Ações</th>
          </tr>
        </thead>
        <tbody>
          {#each orders as order}
            <tr class="border-b border-border last:border-b-0 hover:bg-muted/30 transition-colors">
              <td class="px-4 py-3">
                <div>
                  <span class="font-medium text-foreground">{order.name}</span>
                  {#if order.order_number}
                    <span class="ml-2 text-xs text-muted-foreground">#{order.order_number}</span>
                  {/if}
                </div>
              </td>
              <td class="px-4 py-3 text-muted-foreground">{order.account_name || '—'}</td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {getStatusBadge(order.status)}">
                  {getStatusLabel(order.status)}
                </span>
              </td>
              <td class="px-4 py-3 text-muted-foreground">
                {order.order_date ? formatDate(order.order_date) : '—'}
              </td>
              <td class="px-4 py-3 text-right font-medium text-foreground">
                {formatCurrency(Number(order.total_amount || 0), order.currency || 'BRL')}
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-1">
                  {#if order.status === 'DRAFT'}
                    <Button
                      variant="ghost"
                      size="sm"
                      onclick={() => handleActivate(order.id)}
                      class="h-8 gap-1 text-blue-600 dark:text-blue-400"
                    >
                      <Zap class="size-3.5" />
                      Ativar
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onclick={() => handleDelete(order.id)}
                      class="h-8 text-rose-600 dark:text-rose-400"
                    >
                      <Trash2 class="size-3.5" />
                    </Button>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="flex flex-col items-center justify-center py-16 text-center">
      <div class="mb-4 flex size-16 items-center justify-center rounded-xl bg-muted">
        <ShoppingCart class="size-8 text-muted-foreground" />
      </div>
      <h3 class="text-lg font-medium text-foreground">Nenhum pedido de compra</h3>
      <p class="text-sm text-muted-foreground">
        Crie pedidos de compra para dar entrada no estoque e registrar no financeiro
      </p>
    </div>
  {/if}

  <Pagination
    page={pagination.page}
    limit={pagination.limit}
    total={pagination.total}
    limitOptions={[10, 25, 50]}
    onPageChange={handlePageChange}
    onLimitChange={handleLimitChange}
  />
</div>

<!-- Create Dialog -->
{#if showCreateDialog}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog">
    <div class="mx-4 w-full max-w-lg rounded-xl bg-background p-6 shadow-xl">
      <h2 class="mb-4 text-lg font-semibold text-foreground">Novo Pedido de Compra</h2>

      <div class="space-y-4">
        <div>
          <label for="po-name" class="block text-sm font-medium text-foreground">Nome *</label>
          <input
            id="po-name"
            type="text"
            bind:value={createFormState.name}
            placeholder="Ex: Compra Eletrônicos Março"
            class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div>
          <label for="po-account" class="block text-sm font-medium text-foreground">Fornecedor</label>
          <select
            id="po-account"
            bind:value={createFormState.account}
            class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
          >
            <option value="">Selecionar...</option>
            {#each accounts as acc}
              <option value={acc.value}>{acc.label}</option>
            {/each}
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="po-date" class="block text-sm font-medium text-foreground">Data</label>
            <input
              id="po-date"
              type="date"
              bind:value={createFormState.order_date}
              class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
          </div>
          <div>
            <label for="po-total" class="block text-sm font-medium text-foreground">Valor Total</label>
            <input
              id="po-total"
              type="number"
              step="0.01"
              bind:value={createFormState.total_amount}
              class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
          </div>
        </div>

        <div>
          <label for="po-desc" class="block text-sm font-medium text-foreground">Descrição</label>
          <textarea
            id="po-desc"
            bind:value={createFormState.description}
            rows="2"
            class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
          ></textarea>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-2">
        <Button variant="outline" onclick={() => (showCreateDialog = false)}>Cancelar</Button>
        <Button
          disabled={!createFormState.name.trim()}
          onclick={handleCreate}
        >
          Criar Pedido
        </Button>
      </div>
    </div>
  </div>
{/if}
