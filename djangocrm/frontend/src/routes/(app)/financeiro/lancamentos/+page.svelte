<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/stores';
  import { Button } from '$lib/components/ui/button/index.js';
  import { StatusBadge, TransactionForm } from '$lib/components/financeiro';
  import { SearchableSelect } from '$lib/components/ui/searchable-select/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { formatCurrency, formatDate } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { Plus, Search, X, Repeat } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { financeiro, assistant } from '$lib/api.js';

  let { data } = $props();
  let cur = $derived($orgSettings.default_currency || 'BRL');

  let showCreateModal = $state(false);
  let loading = $state(false);
  let searchInput = $state('');
  let reminderConfig = $state(null);

  $effect(() => {
    if (data?.filters?.search) searchInput = data.filters.search;
  });

  let defaultCurrency = $derived(data.formOptions?.org_currency || cur);

  // Build grouped planos for the filter dropdown
  let planoFilterGroups = $derived.by(() => {
    const planos = data.formOptions?.planos || [];
    const grupos = data.formOptions?.plano_grupos || [];
    if (grupos.length === 0) return [];
    const grupoMap = new Map();
    for (const g of grupos) {
      grupoMap.set(g.id, { label: `${g.codigo} - ${g.nome}`, options: [] });
    }
    for (const p of planos) {
      const group = grupoMap.get(p.grupo_id);
      if (group) {
        group.options.push({ value: p.id, label: p.nome });
      }
    }
    return [...grupoMap.values()].filter((g) => g.options.length > 0);
  });

  let planoFilterOptions = $derived.by(() => {
    if (planoFilterGroups.length > 0) return [];
    return (data.formOptions?.planos || []).map((p) => ({ value: p.id, label: p.nome }));
  });

  let selectedPlano = $state(data.filters?.plano_de_contas || '');

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
    exchange_rate_type: 'FIXO',
    forma_pagamento: '',
    numero_parcelas: 1,
    data_primeiro_vencimento: '',
    is_recorrente: false,
    recorrencia_tipo: '',
    data_fim_recorrencia: ''
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
      exchange_rate_type: 'FIXO',
      currency: defaultCurrency,
      valor_total: '',
      exchange_rate_to_base: '1',
      forma_pagamento: '',
      numero_parcelas: 1,
      data_primeiro_vencimento: '',
      is_recorrente: false,
      recorrencia_tipo: '',
      data_fim_recorrencia: ''
    };
    reminderConfig = null;
  }

  async function handleCreate(fd) {
    loading = true;
    try {
      const created = await financeiro.lancamentos.create({
        ...fd,
        plano_de_contas: fd.plano_de_contas || null,
        account: fd.account || null,
        contact: fd.contact || null,
        opportunity: fd.opportunity || null,
        invoice: fd.invoice || null,
        forma_pagamento: fd.forma_pagamento || null
      });

      // Create reminder if configured inline
      if (reminderConfig && created?.id) {
        try {
          await assistant.createReminder('financeiro.lancamento', created.id, {
            ...reminderConfig,
            name: reminderConfig.name || `Lembrete ${fd.tipo === 'RECEBER' ? 'Receber' : 'Pagar'}`,
          });
        } catch {
          // Reminder creation failed — lancamento was still created successfully
          console.warn('Lembrete não pôde ser criado automaticamente.');
        }
      }

      showCreateModal = false;
      resetForm();
      reminderConfig = null;
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
    if (selectedPlano) params.set('plano_de_contas', selectedPlano);
    goto(`/financeiro/lancamentos?${params.toString()}`);
  }

  function clearFilters() {
    searchInput = '';
    selectedPlano = '';
    goto('/financeiro/lancamentos');
  }

  function handlePlanoFilterChange(val) {
    selectedPlano = val;
    applyFilters();
  }

  let hasActiveFilters = $derived(
    !!(data.filters.search || data.filters.tipo || data.filters.status || selectedPlano)
  );
</script>

<PageHeader title="Lançamentos" subtitle="{data.pagination.total} lançamento{data.pagination.total !== 1 ? 's' : ''}">
  {#snippet actions()}
    <Button onclick={() => { resetForm(); showCreateModal = true; }}>
      <Plus class="mr-1.5 h-4 w-4" />
      <span class="hidden sm:inline">Novo Lançamento</span>
      <span class="sm:hidden">Novo</span>
    </Button>
  {/snippet}
</PageHeader>

<div class="space-y-4 p-4 md:p-6">
  <!-- Filters -->
  <div class="flex flex-wrap items-end gap-2">
    <div class="relative min-w-0 flex-1">
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
    <div class="w-52">
      <SearchableSelect
        bind:value={selectedPlano}
        groups={planoFilterGroups}
        options={planoFilterOptions}
        placeholder="Centro de custo..."
        searchPlaceholder="Buscar centro..."
        emptyText="Nenhum centro encontrado."
        onchange={handlePlanoFilterChange}
      />
    </div>
    {#if hasActiveFilters}
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
          <th class="hidden px-3 py-2.5 text-left font-medium sm:table-cell">Tipo</th>
          <th class="hidden px-3 py-2.5 text-left font-medium md:table-cell">Pessoa</th>
          <th class="hidden px-3 py-2.5 text-left font-medium lg:table-cell">Centro de Custo</th>
          <th class="px-3 py-2.5 text-right font-medium">Valor</th>
          <th class="hidden px-3 py-2.5 text-left font-medium sm:table-cell">Parcelas</th>
          <th class="px-3 py-2.5 text-left font-medium">Status</th>
          <th class="hidden px-3 py-2.5 text-left font-medium sm:table-cell">Vencimento</th>
        </tr>
      </thead>
      <tbody>
        {#each data.lancamentos as item (item.id)}
          <tr
            class="hover:bg-muted/30 cursor-pointer border-b transition-colors"
            onclick={() => goto(`/financeiro/lancamentos/${item.id}`)}
          >
            <td class="max-w-[220px] px-3 py-2.5">
              <span class="block truncate font-medium">{item.descricao}</span>
              {#if item.recorrencia_label}
                <span class="inline-flex items-center gap-0.5 text-[10px] text-blue-600 dark:text-blue-400">
                  <Repeat class="size-2.5" /> {item.recorrencia_label}
                </span>
              {/if}
            </td>
            <td class="hidden px-3 py-2.5 sm:table-cell"><StatusBadge status={item.tipo} /></td>
            <td class="hidden px-3 py-2.5 text-xs md:table-cell">{item.account_name || item.contact_name || '-'}</td>
            <td class="hidden max-w-[150px] truncate px-3 py-2.5 text-xs lg:table-cell">{item.plano_de_contas_nome || '-'}</td>
            <td class="px-3 py-2.5 text-right font-mono text-xs">
              {#if item.is_recorrente}
                {formatCurrency(item.valor_parcela_display, cur)}<span class="text-muted-foreground">/{item.recorrencia_tipo === 'ANUAL' ? 'ano' : item.recorrencia_tipo === 'QUINZENAL' ? 'quinz' : item.recorrencia_tipo === 'SEMANAL' ? 'sem' : 'mês'}</span>
              {:else if item.numero_parcelas > 1}
                {formatCurrency(item.valor_convertido, cur)}
                <span class="text-muted-foreground block text-[10px]">{item.numero_parcelas}x de {formatCurrency(item.valor_parcela_display, cur)}</span>
              {:else}
                {formatCurrency(item.valor_convertido, cur)}
              {/if}
            </td>
            <td class="hidden px-3 py-2.5 text-xs sm:table-cell">{item.parcelas_pagas}</td>
            <td class="px-3 py-2.5"><StatusBadge status={item.status} tipo={item.tipo} /></td>
            <td class="hidden px-3 py-2.5 text-xs sm:table-cell">{formatDate(item.data_primeiro_vencimento)}</td>
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
      bind:reminderConfig
      formOptions={data.formOptions}
      mode="create"
      {loading}
      onsubmit={handleCreate}
      oncancel={() => (showCreateModal = false)}
    />
  </Dialog.Content>
</Dialog.Root>
