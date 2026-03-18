<script>
  import { enhance } from '$app/forms';
  import { invalidateAll, goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { tick, onMount } from 'svelte';
  import { toast } from 'svelte-sonner';
  import {
    Plus,
    Building2,
    Users,
    Target,
    Calendar,
    Eye,
    Globe,
    Phone,
    Mail,
    DollarSign,
    Briefcase,
    MapPin,
    FileText,
    Hash,
    Lock,
    Unlock,
    AlertTriangle,
    Tag,
    UserPlus,
    Contact,
    Banknote,
    Filter,
    CheckSquare
  } from '@lucide/svelte';
  import { PageHeader } from '$lib/components/layout';
  import { CrmDrawer } from '$lib/components/ui/crm-drawer';
  import { CommentSection } from '$lib/components/ui/comment-section';
  import FinancialSummaryCard from '$lib/components/financeiro/FinancialSummaryCard.svelte';
  import { getCurrentUser } from '$lib/api.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
  import { CrmTable } from '$lib/components/ui/crm-table';
  import {
    FilterBar,
    SearchInput,
    SelectFilter,
    DateRangeFilter,
    TagFilter
  } from '$lib/components/ui/filter';
  import { Pagination } from '$lib/components/ui/pagination';
  import { formatRelativeDate, formatCurrency, getInitials } from '$lib/utils/formatting.js';
  import { COUNTRIES, getCountryName } from '$lib/constants/countries.js';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { fetchAddressByCep } from '$lib/utils/viacep.js';
  import { validateCnpj, formatCnpj, fetchCompanyByCnpj } from '$lib/utils/cnpj.js';

  // Column visibility configuration
  const STORAGE_KEY = 'accounts-column-config';

  /**
   * @typedef {'text' | 'email' | 'number' | 'date' | 'select' | 'checkbox' | 'relation'} ColumnType
   * @typedef {{ key: string, label: string, type?: ColumnType, width?: string, editable?: boolean, canHide?: boolean, getValue?: (row: any) => any, emptyText?: string, relationIcon?: string, options?: any[], format?: (value: any) => string }} ColumnDef
   */

  // Industry options for drawer
  const industryOptions = [
    { value: 'ADVERTISING', label: 'Publicidade' },
    { value: 'AGRICULTURE', label: 'Agricultura' },
    { value: 'APPAREL & ACCESSORIES', label: 'Vestuário e Acessórios' },
    { value: 'AUTOMOTIVE', label: 'Automotivo' },
    { value: 'BANKING', label: 'Bancário' },
    { value: 'BIOTECHNOLOGY', label: 'Biotecnologia' },
    { value: 'BUILDING MATERIALS & EQUIPMENT', label: 'Materiais e Equipamentos de Construção' },
    { value: 'CHEMICAL', label: 'Químico' },
    { value: 'COMPUTER', label: 'Informática' },
    { value: 'EDUCATION', label: 'Educação' },
    { value: 'ELECTRONICS', label: 'Eletrônicos' },
    { value: 'ENERGY', label: 'Energia' },
    { value: 'ENTERTAINMENT & LEISURE', label: 'Entretenimento e Lazer' },
    { value: 'FINANCE', label: 'Finanças' },
    { value: 'FOOD & BEVERAGE', label: 'Alimentos e Bebidas' },
    { value: 'GROCERY', label: 'Varejo Alimentar' },
    { value: 'HEALTHCARE', label: 'Saúde' },
    { value: 'INSURANCE', label: 'Seguros' },
    { value: 'LEGAL', label: 'Jurídico' },
    { value: 'MANUFACTURING', label: 'Manufatura' },
    { value: 'PUBLISHING', label: 'Editorial' },
    { value: 'REAL ESTATE', label: 'Imobiliário' },
    { value: 'SERVICE', label: 'Serviços' },
    { value: 'SOFTWARE', label: 'Software' },
    { value: 'SPORTS', label: 'Esportes' },
    { value: 'TECHNOLOGY', label: 'Tecnologia' },
    { value: 'TELECOMMUNICATIONS', label: 'Telecomunicações' },
    { value: 'TELEVISION', label: 'Televisão' },
    { value: 'TRANSPORTATION', label: 'Transporte' },
    { value: 'VENTURE CAPITAL', label: 'Capital de Risco' }
  ];

  // Country options for combobox (id/name format)
  const countryComboOptions = $derived(
    COUNTRIES.map((c) => ({ id: c.code, name: c.name }))
  );

  // Currency options for combobox (id/name format)
  let localCurrencies = $state(/** @type {{ id: string, name: string }[]} */ ([]));
  const allCurrencyOptions = $derived([
    ...CURRENCY_CODES.filter((c) => c.value).map((c) => ({ id: c.value, name: c.label })),
    ...localCurrencies
  ]);

  function handleCreateCurrency(/** @type {string} */ name) {
    const code = name.split(' ')[0].toUpperCase();
    localCurrencies = [...localCurrencies, { id: code, name: name.includes('-') ? name : `${code} - ${name}` }];
    drawerFormData = { ...drawerFormData, currency: code };
    toast.success(`Moeda "${code}" adicionada`);
  }

  // Base drawer columns (using $derived for dynamic currency symbol)
  const baseDrawerColumns = $derived([
    { key: 'name', label: 'Nome', type: 'text' },
    {
      key: 'cnpj',
      label: 'CNPJ',
      type: 'text',
      icon: Building2,
      placeholder: '00.000.000/0000-00'
    },
    {
      key: 'industry',
      label: 'Setor',
      type: 'select',
      icon: Briefcase,
      options: industryOptions,
      placeholder: 'Selecionar setor'
    },
    {
      key: 'website',
      label: 'Site',
      type: 'text',
      icon: Globe,
      placeholder: 'https://exemplo.com'
    },
    { key: 'phone', label: 'Telefone', type: 'text', icon: Phone, placeholder: '+55 (11) 0000-0000' },
    {
      key: 'email',
      label: 'E-mail',
      type: 'email',
      icon: Mail,
      placeholder: 'contato@empresa.com'
    },
    {
      key: 'annualRevenue',
      label: 'Receita',
      type: 'number',
      icon: DollarSign,
      placeholder: '0'
    },
    {
      key: 'currency',
      label: 'Moeda',
      type: 'combobox',
      icon: Banknote,
      options: allCurrencyOptions,
      placeholder: 'Buscar moeda...',
      onCreate: handleCreateCurrency
    },
    {
      key: 'numberOfEmployees',
      label: 'Funcionários',
      type: 'number',
      icon: Users,
      placeholder: '0'
    },
    {
      key: 'addressLine',
      label: 'Endereço',
      type: 'text',
      icon: MapPin,
      placeholder: 'Endereço'
    },
    { key: 'city', label: 'Cidade', type: 'text', placeholder: 'Cidade' },
    { key: 'state', label: 'Estado', type: 'text', placeholder: 'Estado' },
    { key: 'postcode', label: 'CEP', type: 'text', placeholder: 'CEP' },
    {
      key: 'country',
      label: 'País',
      type: 'combobox',
      options: countryComboOptions,
      placeholder: 'Buscar país...'
    },
    {
      key: 'description',
      label: 'Observações',
      type: 'textarea',
      icon: FileText,
      placeholder: 'Adicionar observações sobre esta empresa...'
    }
  ]);

  /** @type {ColumnDef[]} */
  const columns = [
    {
      key: 'name',
      label: 'Empresa',
      type: 'text',
      width: 'w-60',
      canHide: false,
      emptyText: 'Sem nome'
    },
    { key: 'industry', label: 'Setor', type: 'text', width: 'w-40', emptyText: '' },
    {
      key: 'annualRevenue',
      label: 'Receita',
      type: 'number',
      width: 'w-32',
      format: (value, row) => formatCurrency(value, row?.currency || 'BRL', true)
    },
    { key: 'phone', label: 'Telefone', type: 'text', width: 'w-36', emptyText: '' },
    {
      key: 'createdAt',
      label: 'Criado',
      type: 'date',
      width: 'w-36',
      editable: false
    },
    // Hidden by default
    { key: 'website', label: 'Site', type: 'text', width: 'w-44', canHide: true, emptyText: '' }
  ];

  // Default visible columns (excludes website; status removed - using tabs instead)
  const DEFAULT_VISIBLE_COLUMNS = ['name', 'industry', 'annualRevenue', 'phone', 'createdAt'];

  // Column visibility state - use defaults (excludes website)
  let visibleColumns = $state([...DEFAULT_VISIBLE_COLUMNS]);
  let currentUser = $state(null);

  // Load column visibility from localStorage
  onMount(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        visibleColumns = JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse saved columns:', e);
      }
    }
    currentUser = getCurrentUser();
  });

  // Save column visibility when changed
  $effect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(visibleColumns));
    }
  });

  /**
   * Toggle column visibility
   * @param {string} key
   */
  function toggleColumn(key) {
    const col = columns.find((c) => c.key === key);
    if (col?.canHide === false) return;

    if (visibleColumns.includes(key)) {
      visibleColumns = visibleColumns.filter((k) => k !== key);
    } else {
      visibleColumns = [...visibleColumns, key];
    }
  }

  /** @type {{ data: import('./$types').PageData }} */
  let { data } = $props();

  // Computed values from data
  const accounts = $derived(data.accounts || []);
  const pagination = $derived(data.pagination || { page: 1, limit: 10, total: 0, totalPages: 0 });

  // M2M options from API
  const userOptions = $derived((data.users || []).map((u) => ({ id: u.id, name: u.name || u.email || 'N/A', email: u.email || '' })));
  const contactOptions = $derived(
    (data.contacts || []).map((c) => ({ id: c.id, name: c.name, email: c.email }))
  );
  const tagOptions = $derived(
    (data.tags || []).map((/** @type {any} */ t) => ({
      id: t.id,
      name: t.name,
      color: t.color || 'blue'
    }))
  );

  // Drawer columns with dynamic M2M options
  const drawerColumns = $derived([
    ...baseDrawerColumns,
    {
      key: 'assignedTo',
      label: 'Atribuído a',
      type: 'multiselect',
      icon: UserPlus,
      options: userOptions,
      placeholder: 'Selecionar usuários',
      emptyText: 'Não atribuído'
    },
    {
      key: 'contacts',
      label: 'Contatos',
      type: 'multiselect',
      icon: Contact,
      options: contactOptions,
      placeholder: 'Vincular contatos',
      emptyText: 'Nenhum contato'
    },
    {
      key: 'tags',
      label: 'Tags',
      type: 'multiselect',
      icon: Tag,
      options: tagOptions,
      placeholder: 'Adicionar tags',
      emptyText: 'Nenhuma tag'
    }
  ]);

  // Drawer state - simplified for unified drawer
  let drawerOpen = $state(false);
  /** @type {'view' | 'create'} */
  let drawerMode = $state('view');
  /** @type {any} */
  let selectedAccount = $state(null);
  let drawerLoading = $state(false);
  let isSubmitting = $state(false);

  // Empty account template for create mode
  const emptyAccount = {
    name: '',
    cnpj: '',
    industry: '',
    website: '',
    phone: '',
    email: '',
    description: '',
    addressLine: '',
    city: '',
    state: '',
    postcode: '',
    country: '',
    annualRevenue: '',
    currency: '',
    numberOfEmployees: '',
    assignedTo: [],
    contacts: [],
    tags: []
  };

  // Drawer form data - mutable copy of selectedAccount for editing
  let drawerFormData = $state({ ...emptyAccount });

  // Reset form data when account changes or drawer opens
  $effect(() => {
    if (drawerOpen) {
      if (drawerMode === 'create') {
        drawerFormData = { ...emptyAccount, currency: $orgSettings.default_currency || 'BRL' };
      } else if (selectedAccount) {
        drawerFormData = {
          ...selectedAccount,
          currency: selectedAccount.currency || $orgSettings.default_currency || 'BRL'
        };
      }
    }
  });

  // Check if account is closed (inactive)
  const isClosed = $derived(selectedAccount?.isActive === false);

  // URL sync for drawer state
  $effect(() => {
    const viewId = $page.url.searchParams.get('view');
    const action = $page.url.searchParams.get('action');

    if (action === 'create') {
      selectedAccount = null;
      drawerMode = 'create';
      drawerOpen = true;
    } else if (viewId && accounts.length > 0) {
      const account = accounts.find((a) => a.id === viewId);
      if (account) {
        selectedAccount = account;
        drawerMode = 'view';
        drawerOpen = true;
      }
    }
  });

  /**
   * Update URL with drawer state
   * @param {string | null} viewId
   * @param {string | null} action
   * @returns {Promise<void>}
   */
  async function updateUrl(viewId, action) {
    const url = new URL($page.url);
    if (viewId) {
      url.searchParams.set('view', viewId);
      url.searchParams.delete('action');
    } else if (action) {
      url.searchParams.set('action', action);
      url.searchParams.delete('view');
    } else {
      url.searchParams.delete('view');
      url.searchParams.delete('action');
    }
    await goto(url.toString(), { replaceState: true, keepFocus: true });
  }

  /**
   * Open account detail drawer
   * @param {any} account
   */
  function openAccount(account) {
    selectedAccount = account;
    drawerMode = 'view';
    drawerOpen = true;
    updateUrl(account.id, null);
  }

  /**
   * Open create drawer
   */
  function openCreate() {
    selectedAccount = null;
    drawerMode = 'create';
    drawerOpen = true;
    updateUrl(null, 'create');
  }

  /**
   * Close drawer
   * @returns {Promise<void>}
   */
  async function closeDrawer() {
    drawerOpen = false;
    await updateUrl(null, null);
  }

  /**
   * Handle drawer open change
   * @param {boolean} open
   */
  function handleDrawerChange(open) {
    drawerOpen = open;
    if (!open) {
      updateUrl(null, null);
    }
  }

  // Get unique industries from accounts for filter options
  const industries = $derived.by(() => {
    const uniqueIndustries = [...new Set(accounts.map((a) => a.industry).filter(Boolean))];
    return uniqueIndustries.sort();
  });

  // Industry options for filter
  const industryFilterOptions = $derived([
    { value: '', label: 'Todos os Setores' },
    ...industries.map((ind) => ({ value: ind, label: ind }))
  ]);

  // URL-based filter state from server
  const filters = $derived(data.filters);

  // Count active filters
  const activeFiltersCount = $derived.by(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.industry) count++;
    if (filters.assigned_to?.length > 0) count++;
    if (filters.tags?.length > 0) count++;
    if (filters.created_at_gte || filters.created_at_lte) count++;
    return count;
  });

  /**
   * Update URL with new filters
   * @param {Record<string, any>} newFilters
   */
  async function updateFilters(newFilters) {
    const url = new URL($page.url);
    // Clear existing filter params (preserve view/action)
    ['search', 'industry', 'assigned_to', 'tags', 'created_at_gte', 'created_at_lte'].forEach(
      (key) => url.searchParams.delete(key)
    );
    // Set new params
    Object.entries(newFilters).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((v) => url.searchParams.append(key, v));
      } else if (value && value !== 'ALL') {
        url.searchParams.set(key, value);
      }
    });
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  /**
   * Clear all filters
   */
  function clearFilters() {
    updateFilters({});
  }

  /**
   * Handle page change
   * @param {number} newPage
   */
  async function handlePageChange(newPage) {
    const url = new URL($page.url);
    url.searchParams.set('page', newPage.toString());
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  /**
   * Handle limit change
   * @param {number} newLimit
   */
  async function handleLimitChange(newLimit) {
    const url = new URL($page.url);
    url.searchParams.set('limit', newLimit.toString());
    url.searchParams.set('page', '1'); // Reset to first page
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  // Accounts are already filtered server-side, apply chip filter for active/closed
  let statusChipFilter = $state('ALL');

  // Filter panel expansion state
  let filtersExpanded = $state(false);

  const filteredAccounts = $derived.by(() => {
    if (statusChipFilter === 'active') {
      return accounts.filter((a) => a.isActive !== false);
    } else if (statusChipFilter === 'closed') {
      return accounts.filter((a) => a.isActive === false);
    }
    return accounts;
  });

  // Visible column count for the toggle button
  const visibleColumnCount = $derived(visibleColumns.length);
  const totalColumnCount = $derived(columns.length);

  // Status counts for filter chips
  const activeCount = $derived(accounts.filter((a) => a.isActive !== false).length);
  const closedCount = $derived(accounts.filter((a) => a.isActive === false).length);

  // Form references for server actions
  /** @type {HTMLFormElement} */
  let createForm;
  /** @type {HTMLFormElement} */
  let updateForm;
  /** @type {HTMLFormElement} */
  let deleteForm;
  /** @type {HTMLFormElement} */
  let deactivateForm;
  /** @type {HTMLFormElement} */
  let activateForm;

  // Form data state - aligned with API fields
  let formState = $state({
    accountId: '',
    name: '',
    cnpj: '',
    email: '',
    phone: '',
    website: '',
    industry: '',
    description: '',
    address_line: '',
    city: '',
    state: '',
    postcode: '',
    country: '',
    annual_revenue: '',
    currency: '',
    number_of_employees: '',
    assigned_to: '[]',
    contacts: '[]',
    tags: '[]'
  });

  /**
   * Get initials for avatar
   * @param {any} account
   */
  function getAccountInitials(account) {
    return getInitials(account.name, 1);
  }

  /**
   * Handle field change from CrmDrawer - just updates local state
   * @param {string} field
   * @param {any} value
   */
  async function handleDrawerFieldChange(field, value) {
    // Update local form data only - no auto-save
    drawerFormData = { ...drawerFormData, [field]: value };

    // ViaCEP: auto-fill address from CEP
    if (field === 'postcode') {
      const clean = value?.replace(/\D/g, '') || '';
      if (clean.length === 8) {
        const address = await fetchAddressByCep(clean);
        if (address) {
          drawerFormData = { ...drawerFormData, ...address };
          toast.success('Endereço preenchido pelo CEP');
        }
      }
    }

    // CNPJ: auto-fill company data from BrasilAPI
    if (field === 'cnpj') {
      const clean = value?.replace(/\D/g, '') || '';
      if (clean.length === 14) {
        if (!validateCnpj(clean)) {
          toast.error('CNPJ inválido');
          return;
        }
        // Format the CNPJ in the field
        drawerFormData = { ...drawerFormData, cnpj: formatCnpj(clean) };
        const company = await fetchCompanyByCnpj(clean);
        if (company) {
          // Only fill empty fields — never overwrite user-entered data
          const updates = { cnpj: company.cnpj };
          if (!drawerFormData.name) updates.name = company.name;
          if (!drawerFormData.addressLine) updates.addressLine = company.addressLine;
          if (!drawerFormData.city) updates.city = company.city;
          if (!drawerFormData.state) updates.state = company.state;
          if (!drawerFormData.postcode) updates.postcode = company.postcode;
          if (!drawerFormData.country) updates.country = company.country;
          if (!drawerFormData.phone) updates.phone = company.phone;
          if (!drawerFormData.email) updates.email = company.email;
          drawerFormData = { ...drawerFormData, ...updates };
          toast.success('Dados da empresa preenchidos automaticamente');
        } else {
          toast.error('CNPJ não encontrado na base de dados');
        }
      }
    }
  }

  /**
   * Handle save for view/edit mode
   */
  async function handleDrawerUpdate() {
    if (drawerMode !== 'view' || !selectedAccount || isClosed) return;

    isSubmitting = true;
    formState.accountId = selectedAccount.id;
    formState.name = drawerFormData.name || '';
    formState.cnpj = drawerFormData.cnpj?.replace(/\D/g, '') || '';
    formState.email = drawerFormData.email || '';
    formState.phone = drawerFormData.phone || '';
    formState.website = drawerFormData.website || '';
    formState.industry = drawerFormData.industry || '';
    formState.description = drawerFormData.description || '';
    formState.address_line = drawerFormData.addressLine || '';
    formState.city = drawerFormData.city || '';
    formState.state = drawerFormData.state || '';
    formState.postcode = drawerFormData.postcode || '';
    formState.country = drawerFormData.country || '';
    formState.annual_revenue = drawerFormData.annualRevenue?.toString() || '';
    formState.currency = drawerFormData.currency || '';
    formState.number_of_employees = drawerFormData.numberOfEmployees?.toString() || '';
    formState.assigned_to = JSON.stringify(drawerFormData.assignedTo || []);
    formState.contacts = JSON.stringify(drawerFormData.contacts || []);
    formState.tags = JSON.stringify(drawerFormData.tags || []);

    await tick();
    updateForm.requestSubmit();
  }

  /**
   * Handle save for create mode
   */
  async function handleDrawerSave() {
    if (drawerMode !== 'create') return;

    isSubmitting = true;
    formState.name = drawerFormData.name || '';
    formState.cnpj = drawerFormData.cnpj?.replace(/\D/g, '') || '';
    formState.email = drawerFormData.email || '';
    formState.phone = drawerFormData.phone || '';
    formState.website = drawerFormData.website || '';
    formState.industry = drawerFormData.industry || '';
    formState.description = drawerFormData.description || '';
    formState.address_line = drawerFormData.addressLine || '';
    formState.city = drawerFormData.city || '';
    formState.state = drawerFormData.state || '';
    formState.postcode = drawerFormData.postcode || '';
    formState.country = drawerFormData.country || '';
    formState.annual_revenue = drawerFormData.annualRevenue?.toString() || '';
    formState.currency = drawerFormData.currency || '';
    formState.number_of_employees = drawerFormData.numberOfEmployees?.toString() || '';
    formState.assigned_to = JSON.stringify(drawerFormData.assignedTo || []);
    formState.contacts = JSON.stringify(drawerFormData.contacts || []);
    formState.tags = JSON.stringify(drawerFormData.tags || []);

    await tick();
    createForm.requestSubmit();
  }

  /**
   * Handle account delete
   */
  async function handleDelete() {
    if (!selectedAccount) return;
    if (!confirm(`Tem certeza que deseja excluir "${selectedAccount.name}"?`)) return;

    formState.accountId = selectedAccount.id;
    await tick();
    deleteForm.requestSubmit();
  }

  /**
   * Handle account close (deactivate)
   */
  async function handleClose() {
    if (!selectedAccount) return;

    formState.accountId = selectedAccount.id;
    await tick();
    deactivateForm.requestSubmit();
  }

  /**
   * Handle account reopen (activate)
   */
  async function handleReopen() {
    if (!selectedAccount) return;

    formState.accountId = selectedAccount.id;
    await tick();
    activateForm.requestSubmit();
  }

  /**
   * Create enhance handler for form actions
   * @param {string} successMessage
   * @param {boolean} shouldCloseDrawer
   */
  function createEnhanceHandler(successMessage, shouldCloseDrawer = false) {
    return () => {
      return async ({ result }) => {
        isSubmitting = false;
        if (result.type === 'success') {
          toast.success(successMessage);
          if (shouldCloseDrawer) {
            await closeDrawer();
          }
          await invalidateAll();
        } else if (result.type === 'failure') {
          toast.error(result.data?.error || 'Operação falhou');
        } else if (result.type === 'error') {
          toast.error('Ocorreu um erro inesperado');
        }
      };
    };
  }

  /**
   * Navigate to add contact
   */
  function handleAddContact() {
    if (selectedAccount) {
      goto(`/contacts?action=create&accountId=${selectedAccount.id}`);
    }
  }

  /**
   * Navigate to add opportunity
   */
  function handleAddOpportunity() {
    if (selectedAccount) {
      goto(`/opportunities?action=create&accountId=${selectedAccount.id}`);
    }
  }

  /**
   * Navigate to add case
   */
  function handleAddCase() {
    if (selectedAccount) {
      goto(`/cases?action=create&accountId=${selectedAccount.id}`);
    }
  }

  /**
   * Navigate to add task
   */
  function handleAddTask() {
    if (selectedAccount) {
      goto(`/tasks?action=create&accountId=${selectedAccount.id}`);
    }
  }
</script>

<svelte:head>
  <title>Empresas - CRMTalkHub</title>
</svelte:head>

<PageHeader title="Empresas" subtitle="{filteredAccounts.length} de {accounts.length} empresas">
  {#snippet actions()}
    <div class="flex items-center gap-2">
      <!-- Status Filter Chips — hidden below 2xl (1536px) to prevent body-level overflow -->
      <div class="hidden 2xl:flex gap-1">
        <button
          type="button"
          onclick={() => (statusChipFilter = 'ALL')}
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium transition-colors {statusChipFilter ===
          'ALL'
            ? 'bg-[var(--color-primary-default)] text-white'
            : 'bg-[var(--surface-sunken)] text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]'}"
        >
          Todas
          <span
            class="rounded-full px-1.5 py-0.5 text-xs {statusChipFilter === 'ALL'
              ? 'bg-[var(--color-primary-dark)] text-white/90'
              : 'bg-[var(--border-default)] text-[var(--text-tertiary)]'}"
          >
            {accounts.length}
          </span>
        </button>
        <button
          type="button"
          onclick={() => (statusChipFilter = 'active')}
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium transition-colors {statusChipFilter ===
          'active'
            ? 'bg-[var(--color-success-default)] text-white'
            : 'bg-[var(--surface-sunken)] text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]'}"
        >
          Ativas
          <span
            class="rounded-full px-1.5 py-0.5 text-xs {statusChipFilter === 'active'
              ? 'bg-[var(--color-success-dark)] text-white/90'
              : 'bg-[var(--border-default)] text-[var(--text-tertiary)]'}"
          >
            {activeCount}
          </span>
        </button>
        <button
          type="button"
          onclick={() => (statusChipFilter = 'closed')}
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium transition-colors {statusChipFilter ===
          'closed'
            ? 'bg-[var(--text-secondary)] text-white'
            : 'bg-[var(--surface-sunken)] text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]'}"
        >
          Encerradas
          <span
            class="rounded-full px-1.5 py-0.5 text-xs {statusChipFilter === 'closed'
              ? 'bg-[var(--text-tertiary)] text-white/90'
              : 'bg-[var(--border-default)] text-[var(--text-tertiary)]'}"
          >
            {closedCount}
          </span>
        </button>
      </div>

      <div class="bg-border hidden 2xl:block mx-1 h-6 w-px"></div>

      <!-- Filter Toggle Button -->
      <Button
        variant={filtersExpanded ? 'secondary' : 'outline'}
        size="sm"
        class="gap-2"
        onclick={() => (filtersExpanded = !filtersExpanded)}
      >
        <Filter class="h-4 w-4" />
        Filtros
        {#if activeFiltersCount > 0}
          <span
            class="rounded-full bg-[var(--color-primary-light)] px-1.5 py-0.5 text-xs font-medium text-[var(--color-primary-default)]"
          >
            {activeFiltersCount}
          </span>
        {/if}
      </Button>

      <!-- Column Visibility Dropdown -->
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          {#snippet child({ props })}
            <Button {...props} variant="outline" size="sm" class="gap-2">
              <Eye class="h-4 w-4" />
              Colunas
              {#if visibleColumnCount < totalColumnCount}
                <span
                  class="rounded-full bg-[var(--color-primary-light)] px-1.5 py-0.5 text-xs font-medium text-[var(--color-primary-default)]"
                >
                  {visibleColumnCount}/{totalColumnCount}
                </span>
              {/if}
            </Button>
          {/snippet}
        </DropdownMenu.Trigger>
        <DropdownMenu.Content align="end" class="w-48">
          <DropdownMenu.Label>Alternar colunas</DropdownMenu.Label>
          <DropdownMenu.Separator />
          {#each columns as column (column.key)}
            <DropdownMenu.CheckboxItem
              class=""
              checked={visibleColumns.includes(column.key)}
              onCheckedChange={() => toggleColumn(column.key)}
              disabled={column.canHide === false}
            >
              {column.label}
            </DropdownMenu.CheckboxItem>
          {/each}
        </DropdownMenu.Content>
      </DropdownMenu.Root>
      <Button onclick={openCreate} disabled={false}>
        <Plus class="mr-2 h-4 w-4" />
        Nova Empresa
      </Button>
    </div>
  {/snippet}
</PageHeader>

<div class="flex-1">
  <!-- Collapsible Filter Bar -->
  <FilterBar
    minimal={true}
    expanded={filtersExpanded}
    activeCount={activeFiltersCount}
    onClear={clearFilters}
    class="pb-4"
  >
    <SearchInput
      value={filters.search}
      onchange={(value) => updateFilters({ ...filters, search: value })}
      placeholder="Buscar empresas..."
    />
    <SelectFilter
      label="Setor"
      options={industryFilterOptions}
      value={filters.industry}
      onchange={(value) => updateFilters({ ...filters, industry: value })}
    />
    <DateRangeFilter
      label="Criado em"
      startDate={filters.created_at_gte}
      endDate={filters.created_at_lte}
      onchange={(start, end) =>
        updateFilters({ ...filters, created_at_gte: start, created_at_lte: end })}
    />
    <TagFilter
      tags={tagOptions}
      value={filters.tags}
      onchange={(ids) => updateFilters({ ...filters, tags: ids })}
    />
  </FilterBar>
  <!-- Accounts Table -->
  {#if filteredAccounts.length === 0}
    <div class="flex flex-col items-center justify-center py-16 text-center">
      <div
        class="mb-4 flex size-16 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--surface-sunken)]"
      >
        <Building2 class="size-8 text-[var(--text-tertiary)]" />
      </div>
      <h3 class="text-lg font-medium text-[var(--text-primary)]">Nenhuma empresa encontrada</h3>
      <p class="mt-1 text-sm text-[var(--text-secondary)]">
        Tente ajustar seus filtros ou crie uma nova empresa
      </p>
    </div>
  {:else}
    <!-- Desktop Table using CrmTable -->
    <div class="hidden md:block">
      <CrmTable
        data={filteredAccounts}
        {columns}
        bind:visibleColumns
        onRowClick={(row) => openAccount(row)}
      >
        {#snippet emptyState()}
          <div class="flex flex-col items-center justify-center py-16 text-center">
            <div
              class="mb-4 flex size-16 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--surface-sunken)]"
            >
              <Building2 class="size-8 text-[var(--text-tertiary)]" />
            </div>
            <h3 class="text-lg font-medium text-[var(--text-primary)]">Nenhuma empresa encontrada</h3>
          </div>
        {/snippet}
      </CrmTable>
    </div>

    <!-- Mobile Card View -->
    <div class="divide-y divide-[var(--border-default)] md:hidden">
      {#each filteredAccounts as account (account.id)}
        <button
          type="button"
          class="flex w-full items-start gap-4 p-4 text-left transition-colors hover:bg-[var(--surface-sunken)] {!account.isActive
            ? 'opacity-60'
            : ''}"
          onclick={() => openAccount(account)}
        >
          <div
            class="flex size-12 shrink-0 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary-default)] text-sm font-medium text-white"
          >
            {getAccountInitials(account)}
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="font-medium text-[var(--text-primary)]">{account.name}</p>
                <div class="mt-1 flex items-center gap-1.5">
                  {#if account.isActive !== false}
                    <span
                      class="inline-flex items-center rounded-full bg-[var(--color-success-light)] px-2.5 py-1 text-xs font-medium text-[var(--color-success-default)] dark:bg-[var(--color-success-default)]/15"
                    >
                      Ativa
                    </span>
                  {:else}
                    <span
                      class="inline-flex items-center rounded-full bg-[var(--surface-sunken)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)]"
                    >
                      Encerrada
                    </span>
                  {/if}
                </div>
              </div>
            </div>
            <div
              class="mt-2 flex flex-wrap items-center gap-3 text-sm text-[var(--text-secondary)]"
            >
              {#if account.industry}
                <span>{account.industry}</span>
              {/if}
              <div class="flex items-center gap-1">
                <Users class="size-3.5 text-[var(--text-tertiary)]" />
                <span>{account.contactCount || 0}</span>
              </div>
              <div class="flex items-center gap-1">
                <Target class="size-3.5 text-[var(--text-tertiary)]" />
                <span>{account.opportunityCount || 0}</span>
              </div>
              <div class="flex items-center gap-1">
                <Calendar class="size-3.5 text-[var(--text-tertiary)]" />
                <span>{formatRelativeDate(account.createdAt)}</span>
              </div>
            </div>
          </div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Pagination -->
  <Pagination
    page={pagination.page}
    limit={pagination.limit}
    total={pagination.total}
    onPageChange={handlePageChange}
    onLimitChange={handleLimitChange}
  />
</div>

<!-- Account Drawer -->
<CrmDrawer
  bind:open={drawerOpen}
  onOpenChange={handleDrawerChange}
  data={drawerFormData}
  columns={drawerColumns}
  titleKey="name"
  titlePlaceholder="Nome da empresa"
  headerLabel="Empresa"
  mode={drawerMode}
  loading={drawerLoading || isSubmitting}
  onFieldChange={handleDrawerFieldChange}
  onDelete={handleDelete}
  onClose={closeDrawer}
>
  {#snippet activitySection()}
    <!-- Closed account warning -->
    {#if isClosed && drawerMode !== 'create'}
      <div
        class="mb-4 rounded-[var(--radius-lg)] border border-[var(--color-negative-light)] bg-[var(--color-negative-light)] p-3 dark:border-[var(--color-negative-default)]/30 dark:bg-[var(--color-negative-default)]/10"
      >
        <div class="flex gap-2">
          <AlertTriangle class="mt-0.5 size-4 shrink-0 text-[var(--color-negative-default)]" />
          <div>
            <p class="text-sm font-medium text-[var(--color-negative-default)]">
              Esta empresa está encerrada
            </p>
            <p class="mt-0.5 text-xs text-[var(--color-negative-default)]/80">
              Reabra a empresa para fazer alterações
            </p>
          </div>
        </div>
      </div>
    {/if}

    <!-- Related entity stats (view mode only) -->
    {#if drawerMode !== 'create' && selectedAccount}
      <div class="mb-4">
        <p class="mb-2 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
          Relacionados
        </p>
        <div class="grid grid-cols-4 gap-2">
          <div class="rounded-[var(--radius-lg)] bg-[var(--surface-sunken)] p-2 text-center">
            <div class="flex items-center justify-center gap-1 text-[var(--text-tertiary)]">
              <Users class="size-3.5" />
            </div>
            <p class="mt-0.5 text-lg font-semibold text-[var(--text-primary)]">
              {selectedAccount.contactCount || 0}
            </p>
            <p class="text-[10px] text-[var(--text-secondary)]">Contatos</p>
          </div>
          <div class="rounded-[var(--radius-lg)] bg-[var(--surface-sunken)] p-2 text-center">
            <div class="flex items-center justify-center gap-1 text-[var(--text-tertiary)]">
              <Target class="size-3.5" />
            </div>
            <p class="mt-0.5 text-lg font-semibold text-[var(--text-primary)]">
              {selectedAccount.opportunityCount || 0}
            </p>
            <p class="text-[10px] text-[var(--text-secondary)]">Negócios</p>
          </div>
          <div class="rounded-[var(--radius-lg)] bg-[var(--surface-sunken)] p-2 text-center">
            <div class="flex items-center justify-center gap-1 text-[var(--text-tertiary)]">
              <AlertTriangle class="size-3.5" />
            </div>
            <p class="mt-0.5 text-lg font-semibold text-[var(--text-primary)]">
              {selectedAccount.caseCount || 0}
            </p>
            <p class="text-[10px] text-[var(--text-secondary)]">Casos</p>
          </div>
          <div class="rounded-[var(--radius-lg)] bg-[var(--surface-sunken)] p-2 text-center">
            <div class="flex items-center justify-center gap-1 text-[var(--text-tertiary)]">
              <CheckSquare class="size-3.5" />
            </div>
            <p class="mt-0.5 text-lg font-semibold text-[var(--text-primary)]">
              {selectedAccount.taskCount || 0}
            </p>
            <p class="text-[10px] text-[var(--text-secondary)]">Tarefas</p>
          </div>
        </div>
      </div>

      <!-- Quick actions (for active accounts only) -->
      {#if !isClosed}
        <div class="mb-4">
          <p class="mb-2 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
            Ações Rápidas
          </p>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" onclick={handleAddContact} class="flex-1">
              <Users class="mr-1.5 h-3.5 w-3.5" />
              Adicionar Contato
            </Button>
            <Button variant="outline" size="sm" onclick={handleAddOpportunity} class="flex-1">
              <Target class="mr-1.5 h-3.5 w-3.5" />
              Adicionar Negócio
            </Button>
          </div>
          <div class="mt-2 flex gap-2">
            <Button variant="outline" size="sm" onclick={handleAddCase} class="flex-1">
              <AlertTriangle class="mr-1.5 h-3.5 w-3.5" />
              Adicionar Caso
            </Button>
            <Button variant="outline" size="sm" onclick={handleAddTask} class="flex-1">
              <CheckSquare class="mr-1.5 h-3.5 w-3.5" />
              Adicionar Tarefa
            </Button>
          </div>
        </div>
      {/if}

      <!-- Metadata -->
      <div>
        <p class="mb-2 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
          Detalhes
        </p>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p class="text-xs text-[var(--text-tertiary)]">Responsável</p>
            <p class="font-medium text-[var(--text-primary)]">
              {selectedAccount.owner?.name || 'Não atribuído'}
            </p>
          </div>
          <div>
            <p class="text-xs text-[var(--text-tertiary)]">Criado</p>
            <p class="font-medium text-[var(--text-primary)]">
              {formatRelativeDate(selectedAccount.createdAt)}
            </p>
          </div>
        </div>
      </div>

      <!-- Financial Summary -->
      <div class="mt-6 border-t border-[var(--border-default)] pt-4">
        <FinancialSummaryCard entityId={selectedAccount.id} entityType="account" />
      </div>

      <!-- Comments Section -->
      <div class="mt-6 border-t border-[var(--border-default)] pt-4">
        <CommentSection
          entityId={selectedAccount.id}
          entityType="accounts"
          initialComments={selectedAccount.comments || []}
          currentUserEmail={currentUser?.email}
          isAdmin={currentUser?.organizations?.some((o) => o.role === 'ADMIN')}
        />
      </div>
    {/if}
  {/snippet}

  {#snippet footerActions()}
    {#if drawerMode === 'create'}
      <Button variant="outline" onclick={closeDrawer} disabled={isSubmitting}>Cancelar</Button>
      <Button onclick={handleDrawerSave} disabled={isSubmitting || !drawerFormData.name?.trim()}>
        {isSubmitting ? 'Criando...' : 'Criar Empresa'}
      </Button>
    {:else if isClosed}
      <Button variant="outline" onclick={closeDrawer} disabled={isSubmitting}>Cancelar</Button>
      <Button
        variant="outline"
        class="text-[var(--color-success-default)] hover:text-[var(--color-success-dark)]"
        onclick={handleReopen}
        disabled={isSubmitting}
      >
        <Unlock class="mr-1.5 size-4" />
        Reabrir Empresa
      </Button>
    {:else}
      <Button variant="outline" onclick={closeDrawer} disabled={isSubmitting}>Cancelar</Button>
      <Button
        variant="ghost"
        class="text-[var(--color-primary-default)] hover:text-[var(--color-primary-dark)]"
        onclick={handleClose}
        disabled={isSubmitting}
      >
        <Lock class="mr-1.5 size-4" />
        Encerrar Empresa
      </Button>
      <Button onclick={handleDrawerUpdate} disabled={isSubmitting || !drawerFormData.name?.trim()}>
        {isSubmitting ? 'Salvando...' : 'Salvar'}
      </Button>
    {/if}
  {/snippet}
</CrmDrawer>

<!-- Hidden forms for server actions -->
<form
  method="POST"
  action="?/create"
  bind:this={createForm}
  use:enhance={createEnhanceHandler('Empresa criada com sucesso', true)}
  class="hidden"
>
  <input type="hidden" name="name" value={formState.name} />
  <input type="hidden" name="cnpj" value={formState.cnpj} />
  <input type="hidden" name="email" value={formState.email} />
  <input type="hidden" name="phone" value={formState.phone} />
  <input type="hidden" name="website" value={formState.website} />
  <input type="hidden" name="industry" value={formState.industry} />
  <input type="hidden" name="description" value={formState.description} />
  <input type="hidden" name="address_line" value={formState.address_line} />
  <input type="hidden" name="city" value={formState.city} />
  <input type="hidden" name="state" value={formState.state} />
  <input type="hidden" name="postcode" value={formState.postcode} />
  <input type="hidden" name="country" value={formState.country} />
  <input type="hidden" name="annual_revenue" value={formState.annual_revenue} />
  <input type="hidden" name="currency" value={formState.currency} />
  <input type="hidden" name="number_of_employees" value={formState.number_of_employees} />
  <input type="hidden" name="assigned_to" value={formState.assigned_to} />
  <input type="hidden" name="contacts" value={formState.contacts} />
  <input type="hidden" name="tags" value={formState.tags} />
</form>

<form
  method="POST"
  action="?/update"
  bind:this={updateForm}
  use:enhance={createEnhanceHandler('Empresa atualizada com sucesso', true)}
  class="hidden"
>
  <input type="hidden" name="accountId" value={formState.accountId} />
  <input type="hidden" name="name" value={formState.name} />
  <input type="hidden" name="cnpj" value={formState.cnpj} />
  <input type="hidden" name="email" value={formState.email} />
  <input type="hidden" name="phone" value={formState.phone} />
  <input type="hidden" name="website" value={formState.website} />
  <input type="hidden" name="industry" value={formState.industry} />
  <input type="hidden" name="description" value={formState.description} />
  <input type="hidden" name="address_line" value={formState.address_line} />
  <input type="hidden" name="city" value={formState.city} />
  <input type="hidden" name="state" value={formState.state} />
  <input type="hidden" name="postcode" value={formState.postcode} />
  <input type="hidden" name="country" value={formState.country} />
  <input type="hidden" name="annual_revenue" value={formState.annual_revenue} />
  <input type="hidden" name="currency" value={formState.currency} />
  <input type="hidden" name="number_of_employees" value={formState.number_of_employees} />
  <input type="hidden" name="assigned_to" value={formState.assigned_to} />
  <input type="hidden" name="contacts" value={formState.contacts} />
  <input type="hidden" name="tags" value={formState.tags} />
</form>

<form
  method="POST"
  action="?/delete"
  bind:this={deleteForm}
  use:enhance={createEnhanceHandler('Empresa excluída com sucesso', true)}
  class="hidden"
>
  <input type="hidden" name="accountId" value={formState.accountId} />
</form>

<form
  method="POST"
  action="?/deactivate"
  bind:this={deactivateForm}
  use:enhance={createEnhanceHandler('Empresa encerrada com sucesso', true)}
  class="hidden"
>
  <input type="hidden" name="accountId" value={formState.accountId} />
</form>

<form
  method="POST"
  action="?/activate"
  bind:this={activateForm}
  use:enhance={createEnhanceHandler('Empresa reaberta com sucesso')}
  class="hidden"
>
  <input type="hidden" name="accountId" value={formState.accountId} />
</form>
