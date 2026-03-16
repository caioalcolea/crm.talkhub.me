<script>
  import { page } from '$app/stores';
  import { goto, invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import { tick } from 'svelte';
  import { toast } from 'svelte-sonner';

  import { PageHeader } from '$lib/components/layout';
  import { CrmDrawer } from '$lib/components/ui/crm-drawer';
  import { CrmTable } from '$lib/components/ui/crm-table';
  import { FilterBar, SearchInput, SelectFilter } from '$lib/components/ui/filter';
  import { Pagination } from '$lib/components/ui/pagination';
  import { Button } from '$lib/components/ui/button';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { Package, ArrowLeft, Filter, Columns3, Plus, AlertTriangle } from '@lucide/svelte';

  /** @type {{ data: import('./$types').PageData }} */
  let { data } = $props();

  // Status/Type options
  const STATUS_OPTIONS = [
    { value: 'true', label: 'Ativo' },
    { value: 'false', label: 'Inativo' }
  ];

  const TYPE_OPTIONS = [
    { value: 'product', label: 'Produto' },
    { value: 'service', label: 'Serviço' }
  ];

  /** @type {Array<{key: string, label: string, type?: string, width?: string, editable?: boolean, canHide?: boolean, getValue?: (row: any) => any}>} */
  const columns = [
    {
      key: 'name',
      label: 'Nome',
      type: 'text',
      width: 'w-48',
      canHide: false
    },
    {
      key: 'product_type',
      label: 'Tipo',
      type: 'text',
      width: 'w-24',
      canHide: true,
    },
    {
      key: 'sku',
      label: 'SKU',
      type: 'text',
      width: 'w-28',
      canHide: true,
    },
    {
      key: 'category',
      label: 'Categoria',
      type: 'text',
      width: 'w-32',
      canHide: true,
    },
    {
      key: 'price',
      label: 'Preço Venda',
      type: 'number',
      width: 'w-28',
      canHide: false,
    },
    {
      key: 'cost_price',
      label: 'Custo',
      type: 'number',
      width: 'w-28',
      canHide: true,
    },
    {
      key: 'margin_percent',
      label: 'Margem %',
      type: 'number',
      width: 'w-24',
      canHide: true,
    },
    {
      key: 'stock_quantity',
      label: 'Estoque',
      type: 'number',
      width: 'w-24',
      canHide: true,
    },
    {
      key: 'default_tax_rate',
      label: 'Imposto %',
      type: 'number',
      width: 'w-24',
      canHide: true,
    }
  ];

  // Drawer field definitions
  const drawerFields = [
    { key: 'name', label: 'Nome', type: 'text', section: 'core', required: true },
    { key: 'product_type', label: 'Tipo', type: 'select', section: 'core', options: TYPE_OPTIONS },
    { key: 'sku', label: 'SKU', type: 'text', section: 'core' },
    { key: 'category', label: 'Categoria', type: 'text', section: 'core' },
    { key: 'unit_of_measure', label: 'Unidade de Medida', type: 'text', section: 'core' },
    { key: 'price', label: 'Preço de Venda', type: 'number', section: 'pricing' },
    { key: 'cost_price', label: 'Preço de Custo', type: 'number', section: 'pricing' },
    { key: 'currency', label: 'Moeda', type: 'text', section: 'pricing' },
    { key: 'default_tax_rate', label: 'Imposto Padrão (%)', type: 'number', section: 'taxes' },
    { key: 'gateway_fee_percent', label: 'Taxa Gateway (%)', type: 'number', section: 'taxes' },
    { key: 'gateway_fee_fixed', label: 'Taxa Fixa (R$)', type: 'number', section: 'taxes' },
    { key: 'track_inventory', label: 'Controlar Estoque', type: 'boolean', section: 'inventory' },
    { key: 'stock_quantity', label: 'Quantidade em Estoque', type: 'number', section: 'inventory' },
    { key: 'stock_min_alert', label: 'Estoque Mínimo (Alerta)', type: 'number', section: 'inventory' },
    { key: 'isActive', label: 'Ativo', type: 'boolean', section: 'settings' },
    { key: 'description', label: 'Descrição', type: 'textarea', section: 'details' }
  ];

  const DEFAULT_VISIBLE_COLUMNS = ['name', 'product_type', 'sku', 'category', 'price', 'cost_price', 'margin_percent', 'stock_quantity'];

  // State
  let filtersExpanded = $state(false);
  let visibleColumns = $state([...DEFAULT_VISIBLE_COLUMNS]);

  // Drawer state
  let drawerOpen = $state(false);
  /** @type {'view' | 'create'} */
  let drawerMode = $state('view');
  let selectedProduct = $state(null);
  /** @type {Record<string, any>} */
  let drawerFormData = $state({});

  // Form references
  let createForm;
  let updateForm;
  let deleteForm;

  // Form state for hidden forms
  let formState = $state({
    productId: '',
    name: '',
    description: '',
    sku: '',
    product_type: 'product',
    price: '0',
    cost_price: '0',
    currency: 'BRL',
    category: '',
    isActive: 'true',
    default_tax_rate: '0',
    gateway_fee_percent: '0',
    gateway_fee_fixed: '0',
    track_inventory: 'false',
    stock_quantity: '0',
    stock_min_alert: '0',
    unit_of_measure: 'un'
  });

  // Derived values
  const filters = $derived(data.filters);
  const pagination = $derived(data.pagination);
  const products = $derived(data.products);
  const categories = $derived(data.categories || []);

  const activeFiltersCount = $derived(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.category) count++;
    if (filters.is_active) count++;
    if (filters.product_type) count++;
    return count;
  });

  // Filter handlers
  async function updateFilters(newFilters) {
    const url = new URL($page.url);
    ['search', 'category', 'is_active', 'product_type'].forEach((key) => url.searchParams.delete(key));
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

  function handleRowClick(product) {
    selectedProduct = product;
    drawerMode = 'view';
    drawerOpen = true;
  }

  function openCreateDrawer() {
    selectedProduct = null;
    drawerMode = 'create';
    drawerFormData = {
      name: '',
      description: '',
      sku: '',
      product_type: 'product',
      price: '0',
      cost_price: '0',
      currency: 'BRL',
      category: '',
      isActive: true,
      default_tax_rate: '0',
      gateway_fee_percent: '0',
      gateway_fee_fixed: '0',
      track_inventory: false,
      stock_quantity: '0',
      stock_min_alert: '0',
      unit_of_measure: 'un'
    };
    drawerOpen = true;
  }

  function closeDrawer() {
    drawerOpen = false;
    selectedProduct = null;
    drawerFormData = {};
  }

  $effect(() => {
    if (drawerOpen) {
      if (drawerMode !== 'create' && selectedProduct) {
        drawerFormData = { ...selectedProduct };
      }
    }
  });

  function handleFieldChange(field, value) {
    drawerFormData[field] = value;
  }

  async function handleDrawerSave() {
    const d = drawerFormData;
    if (drawerMode === 'create') {
      formState.name = d.name || '';
      formState.description = d.description || '';
      formState.sku = d.sku || '';
      formState.product_type = d.product_type || 'product';
      formState.price = d.price?.toString() || '0';
      formState.cost_price = d.cost_price?.toString() || '0';
      formState.currency = d.currency || 'BRL';
      formState.category = d.category || '';
      formState.isActive = d.isActive ? 'true' : 'false';
      formState.default_tax_rate = d.default_tax_rate?.toString() || '0';
      formState.gateway_fee_percent = d.gateway_fee_percent?.toString() || '0';
      formState.gateway_fee_fixed = d.gateway_fee_fixed?.toString() || '0';
      formState.track_inventory = d.track_inventory ? 'true' : 'false';
      formState.stock_quantity = d.stock_quantity?.toString() || '0';
      formState.stock_min_alert = d.stock_min_alert?.toString() || '0';
      formState.unit_of_measure = d.unit_of_measure || 'un';
      await tick();
      createForm.requestSubmit();
    } else {
      formState.productId = selectedProduct.id;
      formState.name = d.name || '';
      formState.description = d.description || '';
      formState.sku = d.sku || '';
      formState.product_type = d.product_type || 'product';
      formState.price = d.price?.toString() || '0';
      formState.cost_price = d.cost_price?.toString() || '0';
      formState.currency = d.currency || 'BRL';
      formState.category = d.category || '';
      formState.isActive = d.isActive ? 'true' : 'false';
      formState.default_tax_rate = d.default_tax_rate?.toString() || '0';
      formState.gateway_fee_percent = d.gateway_fee_percent?.toString() || '0';
      formState.gateway_fee_fixed = d.gateway_fee_fixed?.toString() || '0';
      formState.track_inventory = d.track_inventory ? 'true' : 'false';
      formState.stock_quantity = d.stock_quantity?.toString() || '0';
      formState.stock_min_alert = d.stock_min_alert?.toString() || '0';
      formState.unit_of_measure = d.unit_of_measure || 'un';
      await tick();
      updateForm.requestSubmit();
    }
  }

  async function handleDelete() {
    if (!selectedProduct) return;
    if (!confirm('Tem certeza que deseja excluir este produto/serviço?')) return;
    formState.productId = selectedProduct.id;
    await tick();
    deleteForm.requestSubmit();
  }

  // Column visibility
  function loadColumnConfig() {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('products-column-config');
      if (saved) {
        try { visibleColumns = JSON.parse(saved); }
        catch { visibleColumns = [...DEFAULT_VISIBLE_COLUMNS]; }
      }
    }
  }

  function saveColumnConfig() {
    if (typeof window !== 'undefined') {
      localStorage.setItem('products-column-config', JSON.stringify(visibleColumns));
    }
  }

  function toggleColumn(key) {
    const column = columns.find((c) => c.key === key);
    if (column && column.canHide === false) return;
    if (visibleColumns.includes(key)) {
      visibleColumns = visibleColumns.filter((k) => k !== key);
    } else {
      visibleColumns = [...visibleColumns, key];
    }
    saveColumnConfig();
  }

  $effect(() => { loadColumnConfig(); });
</script>

<!-- Hidden Forms -->
<form
  bind:this={createForm}
  method="POST"
  action="?/create"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'success') {
        toast.success('Produto/Serviço criado');
        closeDrawer();
        invalidateAll();
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao criar');
      }
    };
  }}
>
  <input type="hidden" name="name" value={formState.name} />
  <input type="hidden" name="description" value={formState.description} />
  <input type="hidden" name="sku" value={formState.sku} />
  <input type="hidden" name="product_type" value={formState.product_type} />
  <input type="hidden" name="price" value={formState.price} />
  <input type="hidden" name="cost_price" value={formState.cost_price} />
  <input type="hidden" name="currency" value={formState.currency} />
  <input type="hidden" name="category" value={formState.category} />
  <input type="hidden" name="isActive" value={formState.isActive} />
  <input type="hidden" name="default_tax_rate" value={formState.default_tax_rate} />
  <input type="hidden" name="gateway_fee_percent" value={formState.gateway_fee_percent} />
  <input type="hidden" name="gateway_fee_fixed" value={formState.gateway_fee_fixed} />
  <input type="hidden" name="track_inventory" value={formState.track_inventory} />
  <input type="hidden" name="stock_quantity" value={formState.stock_quantity} />
  <input type="hidden" name="stock_min_alert" value={formState.stock_min_alert} />
  <input type="hidden" name="unit_of_measure" value={formState.unit_of_measure} />
</form>

<form
  bind:this={updateForm}
  method="POST"
  action="?/update"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'success') {
        toast.success('Produto/Serviço atualizado');
        closeDrawer();
        invalidateAll();
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao atualizar');
      }
    };
  }}
>
  <input type="hidden" name="productId" value={formState.productId} />
  <input type="hidden" name="name" value={formState.name} />
  <input type="hidden" name="description" value={formState.description} />
  <input type="hidden" name="sku" value={formState.sku} />
  <input type="hidden" name="product_type" value={formState.product_type} />
  <input type="hidden" name="price" value={formState.price} />
  <input type="hidden" name="cost_price" value={formState.cost_price} />
  <input type="hidden" name="currency" value={formState.currency} />
  <input type="hidden" name="category" value={formState.category} />
  <input type="hidden" name="isActive" value={formState.isActive} />
  <input type="hidden" name="default_tax_rate" value={formState.default_tax_rate} />
  <input type="hidden" name="gateway_fee_percent" value={formState.gateway_fee_percent} />
  <input type="hidden" name="gateway_fee_fixed" value={formState.gateway_fee_fixed} />
  <input type="hidden" name="track_inventory" value={formState.track_inventory} />
  <input type="hidden" name="stock_quantity" value={formState.stock_quantity} />
  <input type="hidden" name="stock_min_alert" value={formState.stock_min_alert} />
  <input type="hidden" name="unit_of_measure" value={formState.unit_of_measure} />
</form>

<form
  bind:this={deleteForm}
  method="POST"
  action="?/delete"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'success') {
        toast.success('Produto/Serviço excluído');
        closeDrawer();
        invalidateAll();
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao excluir');
      }
    };
  }}
>
  <input type="hidden" name="productId" value={formState.productId} />
</form>

<!-- Page Content -->
<div class="flex flex-col gap-4 p-6">
  <!-- Header -->
  <PageHeader title="Produtos/Serviços">
    {#snippet actions()}
      <Button variant="ghost" size="sm" onclick={() => goto('/invoices')}>
        <ArrowLeft class="mr-2 size-4" />
        Faturas
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

      <DropdownMenu.Root>
        <DropdownMenu.Trigger>
          {#snippet child({ props })}
            <Button {...props} variant="outline" size="sm" class="gap-2">
              <Columns3 class="size-4" />
              Colunas
            </Button>
          {/snippet}
        </DropdownMenu.Trigger>
        <DropdownMenu.Content align="end" class="w-48">
          {#each columns as column}
            <DropdownMenu.CheckboxItem
              checked={visibleColumns.includes(column.key)}
              disabled={column.canHide === false}
              onCheckedChange={() => toggleColumn(column.key)}
            >
              {column.label}
            </DropdownMenu.CheckboxItem>
          {/each}
        </DropdownMenu.Content>
      </DropdownMenu.Root>

      <Button onclick={openCreateDrawer} class="gap-2">
        <Plus class="size-4" />
        Novo
      </Button>
    {/snippet}
  </PageHeader>

  <!-- Filter Bar -->
  <FilterBar
    minimal
    expanded={filtersExpanded}
    activeCount={activeFiltersCount()}
    onClear={clearFilters}
  >
    <SearchInput
      value={filters.search}
      placeholder="Buscar produtos/serviços..."
      onchange={(value) => updateFilters({ ...filters, search: value })}
    />

    <SelectFilter
      label="Tipo"
      value={filters.product_type}
      options={TYPE_OPTIONS}
      onchange={(value) => updateFilters({ ...filters, product_type: value })}
    />

    {#if categories.length > 0}
      <SelectFilter
        label="Categoria"
        value={filters.category}
        options={categories}
        onchange={(value) => updateFilters({ ...filters, category: value })}
      />
    {/if}

    <SelectFilter
      label="Status"
      value={filters.is_active}
      options={STATUS_OPTIONS}
      onchange={(value) => updateFilters({ ...filters, is_active: value })}
    />
  </FilterBar>

  <!-- Products Table -->
  <CrmTable data={products} {columns} bind:visibleColumns onRowClick={handleRowClick}>
    {#snippet emptyState()}
      <div class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex size-16 items-center justify-center rounded-xl bg-muted">
          <Package class="size-8 text-muted-foreground" />
        </div>
        <h3 class="text-lg font-medium text-foreground">Nenhum produto/serviço ainda</h3>
        <p class="text-sm text-muted-foreground">
          Crie seu primeiro produto ou serviço para usar nas faturas
        </p>
      </div>
    {/snippet}
    {#snippet cellContent(row, column)}
      {#if column.key === 'product_type'}
        <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {row.product_type === 'service' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}">
          {row.product_type === 'service' ? 'Serviço' : 'Produto'}
        </span>
      {:else if column.key === 'price'}
        {formatCurrency(Number(row.price), row.currency || 'BRL')}
      {:else if column.key === 'cost_price'}
        {formatCurrency(Number(row.cost_price || 0), row.currency || 'BRL')}
      {:else if column.key === 'margin_percent'}
        <span class="font-medium {Number(row.margin_percent || 0) > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">
          {Number(row.margin_percent || 0).toFixed(1)}%
        </span>
      {:else if column.key === 'stock_quantity'}
        {#if row.track_inventory}
          <div class="flex items-center gap-1.5">
            <span class="{row.is_low_stock ? 'text-rose-600 dark:text-rose-400 font-semibold' : ''}">
              {Number(row.stock_quantity || 0)} {row.unit_of_measure || 'un'}
            </span>
            {#if row.is_low_stock}
              <AlertTriangle class="size-3.5 text-rose-500" />
            {/if}
          </div>
        {:else}
          <span class="text-muted-foreground">—</span>
        {/if}
      {:else if column.key === 'default_tax_rate'}
        {Number(row.default_tax_rate || 0) > 0 ? `${Number(row.default_tax_rate).toFixed(1)}%` : '—'}
      {:else}
        {row[column.key] || '—'}
      {/if}
    {/snippet}
  </CrmTable>

  <!-- Pagination -->
  <Pagination
    page={pagination.page}
    limit={pagination.limit}
    total={pagination.total}
    limitOptions={[10, 25, 50, 100]}
    onPageChange={handlePageChange}
    onLimitChange={handleLimitChange}
  />
</div>

<!-- Product Drawer -->
<CrmDrawer
  bind:open={drawerOpen}
  data={drawerFormData}
  columns={drawerFields}
  titleKey="name"
  titlePlaceholder="Novo Produto/Serviço"
  headerLabel={drawerFormData.product_type === 'service' ? 'Serviço' : 'Produto'}
  mode={drawerMode}
  onFieldChange={handleFieldChange}
  onDelete={handleDelete}
  onClose={closeDrawer}
>
  {#snippet footerActions()}
    <div class="flex w-full items-center justify-end gap-2">
      <Button variant="outline" onclick={closeDrawer}>Cancelar</Button>
      <Button onclick={handleDrawerSave}>
        {drawerMode === 'create' ? 'Criar' : 'Salvar Alterações'}
      </Button>
    </div>
  {/snippet}
</CrmDrawer>
