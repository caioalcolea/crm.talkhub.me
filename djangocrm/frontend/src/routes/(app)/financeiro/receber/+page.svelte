<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { ParcelaTable } from '$lib/components/financeiro';
  import { financeiro } from '$lib/api.js';
  import { Search, X, CheckCheck } from '@lucide/svelte';

  let { data } = $props();
  let searchInput = $state('');
  let selectedIds = $state([]);

  $effect(() => {
    if (data?.filters?.search) searchInput = data.filters.search;
  });

  async function handlePay(parcela) {
    try {
      await financeiro.payParcela(parcela.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function handleCancel(parcela) {
    if (!confirm('Cancelar esta parcela?')) return;
    try {
      await financeiro.cancelParcela(parcela.id);
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function handleBulkPay() {
    if (selectedIds.length === 0) return;
    if (!confirm(`Marcar ${selectedIds.length} parcela(s) como recebida(s)?`)) return;
    try {
      await financeiro.bulkPayParcelas(selectedIds);
      selectedIds = [];
      invalidateAll();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  function applyFilters() {
    const params = new URLSearchParams();
    if (searchInput) params.set('search', searchInput);
    if (data.filters.status) params.set('status', data.filters.status);
    goto(`/financeiro/receber?${params.toString()}`);
  }
</script>

<div class="space-y-4 p-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Contas a Receber</h1>
      <p class="text-muted-foreground text-sm">Parcelas de lançamentos do tipo Receber</p>
    </div>
    {#if selectedIds.length > 0}
      <Button onclick={handleBulkPay}>
        <CheckCheck class="mr-1.5 h-4 w-4" />
        Receber {selectedIds.length} selecionada(s)
      </Button>
    {/if}
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-2">
    <div class="relative flex-1">
      <Search class="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
      <input
        type="text"
        bind:value={searchInput}
        placeholder="Buscar..."
        class="border-input bg-background h-9 w-full rounded-md border pl-9 pr-3 text-sm"
        onkeydown={(e) => e.key === 'Enter' && applyFilters()}
      />
    </div>
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
    {#if data.filters.search || data.filters.status}
      <Button variant="ghost" size="sm" onclick={() => { searchInput = ''; goto('/financeiro/receber'); }}>
        <X class="mr-1 h-3.5 w-3.5" /> Limpar
      </Button>
    {/if}
  </div>

  <ParcelaTable
    parcelas={data.parcelas}
    selectable={true}
    bind:selectedIds
    onpay={handlePay}
    oncancel={handleCancel}
  />

  {#if data.pagination.totalPages > 1}
    <div class="flex items-center justify-between text-sm">
      <span class="text-muted-foreground">{data.pagination.total} parcela(s)</span>
      <div class="flex gap-1">
        {#each Array.from({ length: Math.min(data.pagination.totalPages, 10) }, (_, i) => i + 1) as pg}
          <Button
            variant={pg === data.pagination.page ? 'default' : 'outline'}
            size="sm"
            class="h-8 w-8"
            onclick={() => goto(`/financeiro/receber?page=${pg}`)}
          >
            {pg}
          </Button>
        {/each}
      </div>
    </div>
  {/if}
</div>
