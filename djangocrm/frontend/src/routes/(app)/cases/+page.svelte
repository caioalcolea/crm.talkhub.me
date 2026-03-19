<script>
  import { enhance } from '$app/forms';
  import { invalidate, goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount, tick } from 'svelte';
  import { toast } from 'svelte-sonner';
  import {
    Plus,
    Briefcase,
    Building2,
    User,
    Users,
    Flag,
    Tag,
    Circle,
    Calendar,
    Clock,
    FileText,
    MessageSquare,
    Activity,
    Loader2,
    Eye,
    Filter,
    List,
    Columns,
    BarChart3,
    Timer,
    AlertTriangle,
    CircleDot,
    CheckCircle2,
    Ban
  } from '@lucide/svelte';
  import { CaseKanban } from '$lib/components/ui/case-kanban';
  import { PipelineManager } from '$lib/components/ui/pipeline-manager';
  import { apiRequest as clientApiRequest } from '$lib/api.js';
  import { cn } from '$lib/utils.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { PageHeader } from '$lib/components/layout';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
  import { CrmTable } from '$lib/components/ui/crm-table';
  import { CrmDrawer } from '$lib/components/ui/crm-drawer';
  import { CommentSection } from '$lib/components/ui/comment-section';
  import SubtaskList from '$lib/components/ui/subtask-list/SubtaskList.svelte';
  import { RelatedEntitiesPanel } from '$lib/components/ui/related-entities/index.js';
  import ReminderSection from '$lib/components/assistant/ReminderSection.svelte';
  import EntityRunsHistory from '$lib/components/assistant/EntityRunsHistory.svelte';
  import ContactAutocomplete from '$lib/components/contacts/ContactAutocomplete.svelte';
  import {
    FilterBar,
    SearchInput,
    SelectFilter,
    DateRangeFilter,
    TagFilter
  } from '$lib/components/ui/filter';
  import { Pagination } from '$lib/components/ui/pagination';
  import {
    caseStatusOptions,
    caseTypeOptions,
    casePriorityOptions
  } from '$lib/utils/table-helpers.js';
  import { useDrawerState } from '$lib/hooks';

  // Account from URL param (for quick action from account page)
  let accountFromUrl = $state(false);
  let accountName = $state('');
  let accountIdFromUrl = $state('');

  /**
   * @typedef {Object} ColumnDef
   * @property {string} key
   * @property {string} label
   * @property {'text' | 'email' | 'number' | 'date' | 'select' | 'checkbox' | 'relation'} [type]
   * @property {string} [width]
   * @property {{ value: string, label: string, color: string }[]} [options]
   * @property {boolean} [editable]
   * @property {boolean} [canHide]
   * @property {string} [relationIcon]
   * @property {(row: any) => any} [getValue]
   */

  // NotionTable column configuration - reordered for scanning priority
  /** @type {ColumnDef[]} */
  const columns = [
    { key: 'subject', label: 'Chamado', type: 'text', width: 'w-[250px]', canHide: false },
    {
      key: 'account',
      label: 'Conta',
      type: 'relation',
      relationIcon: 'building',
      width: 'w-40',
      getValue: (/** @type {any} */ row) => row.account
    },
    {
      key: 'priority',
      label: 'Prioridade',
      type: 'select',
      options: casePriorityOptions,
      width: 'w-28'
    },
    { key: 'status', label: 'Status', type: 'select', options: caseStatusOptions, width: 'w-28' },
    { key: 'caseType', label: 'Tipo', type: 'select', options: caseTypeOptions, width: 'w-28' },
    { key: 'dueDate', label: 'Prazo', type: 'date', width: 'w-32', canHide: true },
    {
      key: 'dueTime',
      label: 'Hora',
      width: 'w-24',
      canHide: true,
      getValue: (/** @type {any} */ row) => ({ name: row.dueTime ? row.dueTime.slice(0, 5) : '—' })
    },
    {
      key: 'owner',
      label: 'Responsável',
      type: 'relation',
      relationIcon: 'user',
      width: 'w-36',
      getValue: (/** @type {any} */ row) => row.owner
    },
    { key: 'createdAt', label: 'Criado', type: 'date', width: 'w-32', editable: false }
  ];

  // Column visibility state
  const STORAGE_KEY = 'cases-column-config';
  let visibleColumns = $state(columns.map((c) => c.key));
  let currentUser = $derived(data.user ? { ...data.user, organizations: [{ role: data.userRole }] } : null);

  // Load column visibility from localStorage
  onMount(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        visibleColumns = parsed.filter((/** @type {string} */ key) =>
          columns.some((c) => c.key === key)
        );
      } catch (e) {
        console.error('Failed to parse saved columns:', e);
      }
    }
  });

  // Save column visibility when changed
  $effect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visibleColumns));
  });

  /**
   * @param {string} key
   */
  function isColumnVisible(key) {
    return visibleColumns.includes(key);
  }

  /**
   * @param {string} key
   */
  function toggleColumn(key) {
    const column = columns.find((c) => c.key === key);
    // @ts-ignore
    if (column?.canHide === false) return;

    if (visibleColumns.includes(key)) {
      visibleColumns = visibleColumns.filter((k) => k !== key);
    } else {
      visibleColumns = [...visibleColumns, key];
    }
  }

  const columnCounts = $derived({
    visible: visibleColumns.length,
    total: columns.length
  });

  // Drawer local form state
  let drawerFormData = $state({
    subject: '',
    description: '',
    accountId: '',
    accountName: '', // Read-only display for edit mode
    assignedTo: /** @type {string[]} */ ([]),
    contacts: /** @type {string[]} */ ([]),
    teams: /** @type {string[]} */ ([]),
    tags: /** @type {string[]} */ ([]),
    priority: 'Normal',
    caseType: '',
    status: 'New',
    dueDate: '',
    dueTime: '',
    closedOn: ''
  });

  // Track if drawer form has been modified
  let isDrawerDirty = $state(false);
  let isSubmitting = $state(false);

  // ContactAutocomplete state for create mode
  /** @type {any} */
  let selectedContact = $state(null);

  /**
   * Handle contact selection from autocomplete — fills contacts array
   * @param {any} contact
   */
  function handleContactSelected(contact) {
    if (!contact) return;
    drawerFormData = {
      ...drawerFormData,
      contacts: [...new Set([...(drawerFormData.contacts || []), contact.id])]
    };
    isDrawerDirty = true;
  }

  /** @type {{ data: any }} */
  let { data } = $props();

  // Computed values
  let casesData = $derived(data.cases || []);
  const pagination = $derived(data.pagination || { page: 1, limit: 10, total: 0, totalPages: 0 });

  // View mode (list, kanban, or workload)
  /** @type {'list' | 'kanban' | 'workload'} */
  let viewMode = $state('list');

  // Sync viewMode when data changes
  $effect(() => {
    if (data.viewMode) {
      viewMode = data.viewMode;
    }
  });

  // Kanban data from server
  const kanbanData = $derived(data.kanbanData);
  const casePipelines = $derived(data.pipelines || []);
  let activeCasePipelineId = $state('');

  // Pipeline/stage form state for drawer create/edit
  let formPipelineId = $state('');
  let formStageId = $state('');
  const selectedPipelineStages = $derived(
    casePipelines.find(p => p.id === formPipelineId)?.stages
      ?.slice().sort((a, b) => a.order - b.order) ?? []
  );

  $effect(() => {
    if (data.pipelineId) {
      const exists = casePipelines.some(p => p.id === data.pipelineId);
      activeCasePipelineId = exists ? data.pipelineId : (casePipelines[0]?.id || '');
    } else if (casePipelines.length > 0) {
      activeCasePipelineId = casePipelines[0].id;
    }
  });

  async function handleCasePipelineSelect(pipelineId) {
    activeCasePipelineId = pipelineId;
    const url = new URL($page.url);
    if (pipelineId) {
      url.searchParams.set('pipeline_id', pipelineId);
    } else {
      url.searchParams.delete('pipeline_id');
    }
    url.searchParams.set('view', 'kanban');
    await goto(url.toString(), { replaceState: true, noScroll: true });
  }

  async function handleCasePipelineCreate(pipelineData) {
    try {
      await clientApiRequest('/cases/pipelines/', {
        method: 'POST',
        body: pipelineData
      });
      toast.success('Pipeline criado');
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao criar pipeline');
      throw err;
    }
  }

  async function handleCasePipelineDelete(pipelineId) {
    try {
      await clientApiRequest(`/cases/pipelines/${pipelineId}/`, { method: 'DELETE' });
      toast.success('Pipeline excluído');
      if (activeCasePipelineId === pipelineId) activeCasePipelineId = '';
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao excluir pipeline');
      throw err;
    }
  }

  async function handleCasePipelineUpdate(pipelineId, pipelineData) {
    try {
      await clientApiRequest(`/cases/pipelines/${pipelineId}/`, {
        method: 'PUT',
        body: pipelineData
      });
      toast.success('Pipeline atualizado');
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao atualizar pipeline');
      throw err;
    }
  }

  async function handleCaseStageCreate(pipelineId, stageData) {
    try {
      await clientApiRequest(`/cases/pipelines/${pipelineId}/stages/`, {
        method: 'POST',
        body: stageData
      });
      toast.success('Estágio criado');
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao criar estágio');
      throw err;
    }
  }

  async function handleCaseStageUpdate(stageId, stageData) {
    try {
      await clientApiRequest(`/cases/stages/${stageId}/`, {
        method: 'PATCH',
        body: stageData
      });
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao atualizar estágio');
      throw err;
    }
  }

  async function handleCaseStageDelete(stageId) {
    try {
      await clientApiRequest(`/cases/stages/${stageId}/`, { method: 'DELETE' });
      toast.success('Estágio removido');
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao remover estágio');
      throw err;
    }
  }

  async function handleCaseStageReorder(pipelineId, stageOrder) {
    try {
      await clientApiRequest(`/cases/pipelines/${pipelineId}/stages/reorder/`, {
        method: 'POST',
        body: { stage_ids: stageOrder }
      });
      await invalidate('app:cases');
    } catch (err) {
      toast.error(err?.message || 'Erro ao reordenar estágios');
      throw err;
    }
  }

  let isCaseAdmin = $derived(data.userRole === 'ADMIN');
  let pageLoading = $state(false);

  // Lazy-loaded form options (only fetched when drawer opens or kanban view loads)
  let formOptionsLoaded = $state(false);
  let formOptionsLoading = $state(false);
  let lazyFormOptions = $state(
    /** @type {{ accounts: any[], users: any[], contacts: any[], teams: any[], tags: any[] }} */ ({
      accounts: [],
      users: [],
      contacts: [],
      teams: [],
      tags: []
    })
  );

  // Tags from server (always available for TagFilter chip)
  const allTags = $derived(data.formOptions?.tags || []);

  // Derived from lazy-loaded options (used in drawerColumns)
  const accounts = $derived(lazyFormOptions.accounts);
  const users = $derived(lazyFormOptions.users);
  const contacts = $derived(lazyFormOptions.contacts);
  const teams = $derived(lazyFormOptions.teams);
  const tags = $derived(lazyFormOptions.tags.length > 0 ? lazyFormOptions.tags : allTags);

  /**
   * Load form options for drawer — fetches lazily from client API (not on page load)
   */
  async function loadFormOptions() {
    if (formOptionsLoaded || formOptionsLoading) return;

    formOptionsLoading = true;
    try {
      const [accountsRes, usersRes, contactsRes, teamsRes, tagsRes] = await Promise.all([
        clientApiRequest('/accounts/').catch(() => ({})),
        clientApiRequest('/users/').catch(() => ({})),
        clientApiRequest('/contacts/').catch(() => ({})),
        clientApiRequest('/teams/').catch(() => ({})),
        clientApiRequest('/tags/').catch(() => ({}))
      ]);

      // Transform accounts
      let accountsList = [];
      if (accountsRes?.active_accounts?.open_accounts) {
        accountsList = accountsRes.active_accounts.open_accounts;
      } else if (accountsRes?.results) {
        accountsList = accountsRes.results;
      } else if (Array.isArray(accountsRes)) {
        accountsList = accountsRes;
      }

      // Transform users
      const usersList = (usersRes?.active_users?.active_users || []).map((/** @type {any} */ u) => ({
        id: u.id,
        name:
          u.user_details?.first_name && u.user_details?.last_name
            ? `${u.user_details.first_name} ${u.user_details.last_name}`
            : u.user_details?.email || u.email
      }));

      // Transform contacts
      let contactsList = [];
      if (contactsRes?.contact_obj_list) {
        contactsList = contactsRes.contact_obj_list;
      } else if (contactsRes?.results) {
        contactsList = contactsRes.results;
      } else if (Array.isArray(contactsRes)) {
        contactsList = contactsRes;
      }

      // Transform teams
      const teamsList = (teamsRes?.teams || teamsRes?.results || []).map((/** @type {any} */ t) => ({
        id: t.id,
        name: t.name
      }));

      // Transform tags
      const tagsList = (tagsRes?.tags || tagsRes?.results || allTags || []).map((/** @type {any} */ t) => ({
        id: t.id,
        name: t.name,
        color: t.color || 'blue'
      }));

      lazyFormOptions = {
        accounts: accountsList.map((/** @type {any} */ a) => ({ id: a.id, name: a.name })),
        users: usersList,
        contacts: contactsList.map((/** @type {any} */ c) => ({
          id: c.id,
          name: c.first_name && c.last_name ? `${c.first_name} ${c.last_name}` : c.email,
          email: c.email
        })),
        teams: teamsList,
        tags: tagsList
      };
      formOptionsLoaded = true;
    } catch (err) {
      console.error('Failed to load form options:', err);
    } finally {
      formOptionsLoading = false;
    }
  }

  // Eagerly load form options when in kanban view (PipelineManager needs teams/users)
  $effect(() => {
    if (viewMode === 'kanban' && !formOptionsLoaded) {
      loadFormOptions();
    }
  });

  /**
   * Get account name from server-provided accounts list
   * @param {string} id
   */
  function fetchAccountName(id) {
    const account = accounts.find((a) => a.id === id);
    if (account) {
      accountName = account.name;
    } else {
      accountName = 'Conta Desconhecida';
    }
  }

  /**
   * Clear URL params for accountId and action
   */
  function clearUrlParams() {
    const url = new URL($page.url);
    url.searchParams.delete('action');
    url.searchParams.delete('accountId');
    goto(url.pathname, { replaceState: true });
    accountFromUrl = false;
    accountName = '';
    accountIdFromUrl = '';
  }

  // Drawer state using hook
  const drawer = useDrawerState();

  // URL sync for accountId and action params (quick action from account page)
  $effect(() => {
    const action = $page.url.searchParams.get('action');
    const accountIdParam = $page.url.searchParams.get('accountId');

    if (action === 'create' && !drawer.detailOpen) {
      // Handle account pre-fill from URL BEFORE opening drawer
      if (accountIdParam) {
        accountIdFromUrl = accountIdParam;
        accountFromUrl = true;
        fetchAccountName(accountIdParam);
      }

      drawer.openCreate();
      loadFormOptions();

      // Auto-select active pipeline when creating
      if (activeCasePipelineId) {
        const pipeline = casePipelines.find(p => p.id === activeCasePipelineId);
        if (pipeline?.stages?.length) {
          formPipelineId = pipeline.id;
          formStageId = pipeline.stages.slice().sort((a, b) => a.order - b.order)[0].id;
        } else {
          formPipelineId = '';
          formStageId = '';
        }
      } else {
        formPipelineId = '';
        formStageId = '';
      }

      // Set account in form data after drawer opens
      if (accountIdParam) {
        drawerFormData.accountId = accountIdParam;
      }
    }
  });

  // Pre-populate pipeline/stage when opening edit drawer
  $effect(() => {
    const caseItem = drawer.selected;
    if (caseItem && drawer.mode !== 'create') {
      const stageId = caseItem.stage;
      if (stageId) {
        const pipelineForStage = casePipelines.find(p => p.stages?.some(s => s.id === stageId));
        formPipelineId = pipelineForStage?.id ?? '';
        formStageId = stageId;
      } else {
        formPipelineId = '';
        formStageId = '';
      }
    }
  });

  // Account options for drawer select
  const accountOptions = $derived([
    { value: '', label: 'Nenhuma', color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]' },
    ...accounts.map((/** @type {any} */ a) => ({
      value: a.id,
      label: a.name,
      color: 'bg-[var(--color-primary-light)] text-[var(--color-primary-default)]'
    }))
  ]);

  // Drawer columns configuration (with icons and multiselect)
  // Account is only editable on create (and not when pre-filled from URL), read-only on edit
  const drawerColumns = $derived([
    { key: 'subject', label: 'Título do Chamado', type: 'text' },
    // Account field: readonly when pre-filled from URL or in edit mode
    drawer.mode === 'create' && !accountFromUrl
      ? {
          key: 'accountId',
          label: 'Conta',
          type: 'select',
          icon: Building2,
          options: accountOptions,
          emptyText: 'Sem conta'
        }
      : accountFromUrl
        ? {
            key: 'accountDisplay',
            label: 'Conta',
            type: 'readonly',
            icon: Building2,
            getValue: () => accountName || 'Carregando...'
          }
        : {
            key: 'accountName',
            label: 'Conta',
            type: 'readonly',
            icon: Building2,
            emptyText: 'Sem conta'
          },
    {
      key: 'caseType',
      label: 'Tipo',
      type: 'select',
      icon: Tag,
      options: caseTypeOptions,
      emptyText: 'Selecionar tipo'
    },
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      icon: Circle,
      options: caseStatusOptions
    },
    {
      key: 'priority',
      label: 'Prioridade',
      type: 'select',
      icon: Flag,
      options: casePriorityOptions
    },
    {
      key: 'description',
      label: 'Descrição',
      type: 'textarea',
      icon: FileText,
      placeholder: 'Descreva o chamado...',
      emptyText: 'Sem descrição'
    },
    {
      key: 'assignedTo',
      label: 'Responsável',
      type: 'multiselect',
      icon: User,
      options: users.map((/** @type {any} */ u) => ({ id: u.id, name: u.name })),
      emptyText: 'Não atribuído'
    },
    {
      key: 'teams',
      label: 'Equipes',
      type: 'multiselect',
      icon: Users,
      options: teams.map((/** @type {any} */ t) => ({ id: t.id, name: t.name })),
      emptyText: 'Sem equipes'
    },
    {
      key: 'contacts',
      label: 'Contatos',
      type: 'multiselect',
      icon: User,
      options: contacts.map((/** @type {any} */ c) => ({ id: c.id, name: c.name, email: c.email })),
      emptyText: 'Sem contatos'
    },
    {
      key: 'tags',
      label: 'Etiquetas',
      type: 'multiselect',
      icon: Tag,
      options: tags.map((/** @type {any} */ t) => ({ id: t.id, name: t.name })),
      emptyText: 'Sem etiquetas'
    },
    {
      key: 'dueDate',
      label: 'Prazo',
      type: 'date',
      icon: Calendar,
      emptyText: 'Sem prazo'
    },
    {
      key: 'dueTime',
      label: 'Hora',
      type: 'time',
      icon: Clock,
      emptyText: 'Sem hora'
    },
    {
      key: 'closedOn',
      label: 'Data de Encerramento',
      type: 'date',
      icon: Calendar,
      emptyText: 'Não definida'
    }
  ]);

  // Reset drawer form when case changes or drawer opens
  $effect(() => {
    if (drawer.detailOpen) {
      if (drawer.mode === 'create') {
        selectedContact = null;
        drawerFormData = {
          subject: '',
          description: '',
          accountId: accountIdFromUrl || '', // Preserve account from URL if present
          accountName: '',
          assignedTo: [],
          contacts: [],
          teams: [],
          tags: [],
          priority: 'Normal',
          caseType: '',
          status: 'New',
          dueDate: '',
          dueTime: '',
          closedOn: ''
        };
      } else if (drawer.selected) {
        const caseItem = drawer.selected;
        drawerFormData = {
          subject: caseItem.subject || '',
          description: caseItem.description || '',
          accountId: caseItem.account?.id || '',
          accountName: caseItem.account?.name || '', // Read-only display
          assignedTo: (caseItem.assignedTo || []).map((/** @type {any} */ a) => a.id),
          contacts: (caseItem.contacts || []).map((/** @type {any} */ c) => c.id),
          teams: (caseItem.teams || []).map((/** @type {any} */ t) => t.id),
          tags: (caseItem.tags || []).map((/** @type {any} */ t) => t.id),
          priority: caseItem.priority || 'Normal',
          caseType: caseItem.caseType || '',
          status: caseItem.status || 'New',
          dueDate: caseItem.dueDate || '',
          dueTime: caseItem.dueTime || '',
          closedOn: caseItem.closedOn ? caseItem.closedOn.split('T')[0] : ''
        };
      }
      isDrawerDirty = false;
    }
  });

  /**
   * Handle field change from drawer
   * @param {string} field
   * @param {any} value
   */
  function handleDrawerFieldChange(field, value) {
    drawerFormData = { ...drawerFormData, [field]: value };
    isDrawerDirty = true;
  }

  // URL-based filter state from server
  const filters = $derived(data.filters || {});

  // Status options for filter dropdown
  const statusFilterOptions = $derived([
    { value: '', label: 'Todos os Status' },
    ...caseStatusOptions
  ]);

  // Priority options for filter dropdown
  const priorityFilterOptions = $derived([
    { value: '', label: 'Todas as Prioridades' },
    ...casePriorityOptions
  ]);

  // Type options for filter dropdown
  const typeFilterOptions = $derived([{ value: '', label: 'Todos os Tipos' }, ...caseTypeOptions]);

  // Count active filters
  const activeFiltersCount = $derived.by(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.status) count++;
    if (filters.priority) count++;
    if (filters.case_type) count++;
    if (filters.assigned_to?.length > 0) count++;
    if (filters.tags?.length > 0) count++;
    if (filters.created_at_gte || filters.created_at_lte) count++;
    if (filters.quick_filter) count++;
    return count;
  });

  /**
   * Update URL with new filters
   * @param {Record<string, any>} newFilters
   */
  async function updateFilters(newFilters) {
    pageLoading = true;
    const url = new URL($page.url);
    // Clear existing filter params
    [
      'search',
      'status',
      'priority',
      'case_type',
      'assigned_to',
      'tags',
      'created_at_gte',
      'created_at_lte',
      'quick_filter'
    ].forEach((key) => url.searchParams.delete(key));
    // Set new params
    Object.entries(newFilters).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((v) => url.searchParams.append(key, v));
      } else if (value && value !== 'ALL') {
        url.searchParams.set(key, value);
      }
    });
    await goto(url.toString(), { replaceState: true, noScroll: true });
    pageLoading = false;
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
    await goto(url.toString(), { replaceState: true, noScroll: true });
  }

  /**
   * Handle limit change
   * @param {number} newLimit
   */
  async function handleLimitChange(newLimit) {
    const url = new URL($page.url);
    url.searchParams.set('limit', newLimit.toString());
    url.searchParams.set('page', '1'); // Reset to first page
    await goto(url.toString(), { replaceState: true, noScroll: true });
  }

  // Filter panel expansion state
  let filtersExpanded = $state(false);

  // All filtering is server-side via URL params
  const filteredCases = $derived(casesData);

  // ---- Subtask management for Cases ----
  let caseSubtasks = $state(/** @type {any[]} */ ([]));

  $effect(() => {
    if (drawer.selected && drawer.mode !== 'create') {
      loadCaseSubtasks(drawer.selected.id);
    } else {
      caseSubtasks = [];
    }
  });

  async function loadCaseSubtasks(caseId) {
    try {
      const res = await clientApiRequest(`/cases/${caseId}/subtasks/`);
      caseSubtasks = Array.isArray(res) ? res : [];
    } catch {
      caseSubtasks = [];
    }
  }

  async function handleAddCaseSubtask(title) {
    if (!drawer.selected) return;
    try {
      await clientApiRequest(`/cases/${drawer.selected.id}/subtasks/`, {
        method: 'POST',
        body: { title }
      });
      await loadCaseSubtasks(drawer.selected.id);
    } catch {
      toast.error('Erro ao adicionar subtarefa');
    }
  }

  async function handleToggleCaseSubtask(id, completed) {
    try {
      await clientApiRequest(`/cases/subtasks/${id}/`, {
        method: 'PATCH',
        body: { is_completed: completed }
      });
      if (drawer.selected) await loadCaseSubtasks(drawer.selected.id);
    } catch {
      toast.error('Erro ao atualizar subtarefa');
    }
  }

  async function handleUpdateCaseSubtask(id, title) {
    try {
      await clientApiRequest(`/cases/subtasks/${id}/`, {
        method: 'PATCH',
        body: { title }
      });
      if (drawer.selected) await loadCaseSubtasks(drawer.selected.id);
    } catch {
      toast.error('Erro ao atualizar subtarefa');
    }
  }

  async function handleDeleteCaseSubtask(id) {
    try {
      await clientApiRequest(`/cases/subtasks/${id}/`, { method: 'DELETE' });
      if (drawer.selected) await loadCaseSubtasks(drawer.selected.id);
    } catch {
      toast.error('Erro ao remover subtarefa');
    }
  }

  // ---- SLA Dashboard ----
  let slaDashboard = $state(/** @type {any} */ (null));
  let slaDashboardLoading = $state(false);

  async function loadSlaDashboard() {
    slaDashboardLoading = true;
    try {
      slaDashboard = await clientApiRequest('/cases/sla-dashboard/');
    } catch {
      slaDashboard = null;
    }
    slaDashboardLoading = false;
  }

  // Load SLA dashboard on mount
  onMount(() => {
    loadSlaDashboard();
  });

  // SLA status color
  const slaStatusColor = $derived.by(() => {
    if (!slaDashboard || slaDashboard.total_open === 0) return 'emerald';
    const breachRate = slaDashboard.sla_breached_count / slaDashboard.total_open;
    if (breachRate > 0.2) return 'rose';
    if (breachRate > 0.1 || slaDashboard.sla_at_risk_count > 0) return 'amber';
    return 'emerald';
  });

  // ---- Workload view ----
  let caseWorkloadData = $state(/** @type {any[] | null} */ (null));
  let caseWorkloadLoading = $state(false);

  async function loadCaseWorkload() {
    caseWorkloadLoading = true;
    try {
      const res = await clientApiRequest('/cases/workload/');
      caseWorkloadData = res?.workload || [];
    } catch {
      caseWorkloadData = null;
    }
    caseWorkloadLoading = false;
  }

  $effect(() => {
    if (viewMode === 'workload') {
      loadCaseWorkload();
    }
  });

  // ---- Quick filter chips (unified: status + date shortcuts) ----
  /** @type {{ value: string, label: string, color: string|null }[]} */
  const quickFilterOptions = [
    { value: '', label: 'Todos', color: null },
    { value: 'open', label: 'Abertos', color: 'blue' },
    { value: 'closed', label: 'Fechados', color: 'emerald' },
    // separator at index 3
    { value: 'overdue', label: 'Atrasados', color: 'rose' },
    { value: 'due_today', label: 'Vence Hoje', color: 'amber' },
    { value: 'due_this_week', label: 'Esta Semana', color: null },
    { value: 'no_date', label: 'Sem Data', color: null },
  ];

  const activeQuickFilter = $derived(data.filters?.quick_filter || '');

  // Client-side counts for chip badges (approximate — from current page data)
  const chipCounts = $derived.by(() => {
    const openStatuses = ['New', 'Assigned', 'Pending'];
    const closedStatuses = ['Closed', 'Rejected', 'Duplicate'];
    const todayStr = new Date().toISOString().slice(0, 10);
    const now = new Date();
    const dayOfWeek = now.getDay();
    const monday = new Date(now);
    monday.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    const mondayStr = monday.toISOString().slice(0, 10);
    const sundayStr = sunday.toISOString().slice(0, 10);

    return {
      '': pagination.total,
      open: casesData.filter((/** @type {any} */ c) => openStatuses.includes(c.status)).length,
      closed: casesData.filter((/** @type {any} */ c) => closedStatuses.includes(c.status)).length,
      overdue: casesData.filter((/** @type {any} */ c) => c.dueDate && c.dueDate < todayStr && !closedStatuses.includes(c.status)).length,
      due_today: casesData.filter((/** @type {any} */ c) => c.dueDate?.slice(0, 10) === todayStr).length,
      due_this_week: casesData.filter((/** @type {any} */ c) => c.dueDate && c.dueDate >= mondayStr && c.dueDate <= sundayStr).length,
      no_date: casesData.filter((/** @type {any} */ c) => !c.dueDate && !closedStatuses.includes(c.status)).length,
    };
  });

  /**
   * Set quick filter — server-side via URL
   * @param {string} value
   */
  async function setQuickFilter(value) {
    pageLoading = true;
    const url = new URL($page.url);
    url.searchParams.delete('quick_filter');
    url.searchParams.delete('status');
    if (value) {
      url.searchParams.set('quick_filter', value);
    }
    url.searchParams.set('page', '1');
    await goto(url.toString(), { replaceState: true, noScroll: true });
    pageLoading = false;
  }

  // Form references for server actions
  /** @type {HTMLFormElement} */
  let createForm;
  /** @type {HTMLFormElement} */
  let updateForm;
  /** @type {HTMLFormElement} */
  let deleteForm;
  /** @type {HTMLFormElement} */
  let closeForm;
  /** @type {HTMLFormElement} */
  let reopenForm;
  /** @type {HTMLFormElement} */
  let moveCaseForm;

  // Kanban form state for drag-drop
  let kanbanFormState = $state({
    caseId: '',
    status: '',
    stageId: '',
    aboveCaseId: '',
    belowCaseId: ''
  });

  // Form data state
  let formState = $state({
    title: '',
    description: '',
    accountId: '',
    assignedTo: /** @type {string[]} */ ([]),
    contacts: /** @type {string[]} */ ([]),
    teams: /** @type {string[]} */ ([]),
    tags: /** @type {string[]} */ ([]),
    priority: 'Normal',
    caseType: '',
    status: 'New',
    dueDate: '',
    dueTime: '',
    closedOn: '',
    caseId: ''
  });

  /**
   * Handle save from drawer
   */
  async function handleSave() {
    if (!drawerFormData.subject?.trim()) {
      toast.error('O título do chamado é obrigatório');
      return;
    }

    isSubmitting = true;

    // Convert drawer form data to form state
    formState.title = drawerFormData.subject || '';
    formState.description = drawerFormData.description || '';
    formState.accountId = drawerFormData.accountId || '';
    formState.assignedTo = drawerFormData.assignedTo || [];
    formState.contacts = drawerFormData.contacts || [];
    formState.teams = drawerFormData.teams || [];
    formState.tags = drawerFormData.tags || [];
    formState.priority = drawerFormData.priority || 'Normal';
    formState.caseType = drawerFormData.caseType || '';
    formState.status = drawerFormData.status || 'New';
    formState.dueDate = drawerFormData.dueDate || '';
    formState.dueTime = drawerFormData.dueTime || '';
    formState.closedOn = drawerFormData.closedOn || '';

    await tick();

    if (drawer.mode === 'edit' && drawer.selected) {
      formState.caseId = drawer.selected.id;
      await tick();
      updateForm.requestSubmit();
    } else {
      createForm.requestSubmit();
    }
  }

  /**
   * Handle case delete
   */
  async function handleDelete() {
    if (!drawer.selected) return;
    if (!confirm(`Tem certeza que deseja excluir "${drawer.selected.subject}"?`)) return;

    formState.caseId = drawer.selected.id;
    await tick();
    deleteForm.requestSubmit();
  }

  /**
   * Handle case close
   */
  async function handleClose() {
    if (!drawer.selected) return;

    formState.caseId = drawer.selected.id;
    await tick();
    closeForm.requestSubmit();
  }

  /**
   * Handle case reopen
   */
  async function handleReopen() {
    if (!drawer.selected) return;

    formState.caseId = drawer.selected.id;
    await tick();
    reopenForm.requestSubmit();
  }

  /**
   * Create enhance handler for form actions
   * @param {string} successMessage
   * @param {boolean} closeDetailDrawer
   */
  function createEnhanceHandler(successMessage, closeDetailDrawer = false) {
    return () => {
      return async ({ result }) => {
        isSubmitting = false;
        if (result.type === 'success') {
          toast.success(successMessage);
          isDrawerDirty = false;
          if (closeDetailDrawer) {
            drawer.closeDetail();
          } else {
            drawer.closeAll();
          }
          // Clear account URL params if they were set
          if (accountFromUrl) {
            clearUrlParams();
          }
          await invalidate('app:cases');
        } else if (result.type === 'failure') {
          toast.error(result.data?.error || 'Operação falhou');
        } else if (result.type === 'error') {
          toast.error('Ocorreu um erro inesperado');
        }
      };
    };
  }

  /**
   * Convert case to form state for inline editing
   * @param {any} caseItem
   */
  function caseToFormState(caseItem) {
    return {
      caseId: caseItem.id,
      title: caseItem.subject || '',
      description: caseItem.description || '',
      accountId: caseItem.account?.id || '',
      assignedTo: (caseItem.assignedTo || []).map((/** @type {any} */ a) => a.id),
      contacts: (caseItem.contacts || []).map((/** @type {any} */ c) => c.id),
      teams: (caseItem.teams || []).map((/** @type {any} */ t) => t.id),
      tags: (caseItem.tags || []).map((/** @type {any} */ t) => t.id),
      priority: caseItem.priority || 'Normal',
      caseType: caseItem.caseType || '',
      status: caseItem.status || 'New',
      closedOn: caseItem.closedOn ? caseItem.closedOn.split('T')[0] : '',
      dueDate: caseItem.dueDate ? caseItem.dueDate.split('T')[0] : '',
      dueTime: caseItem.dueTime || ''
    };
  }

  /**
   * Handle inline cell edits - persists to API
   * @param {any} caseItem
   * @param {string} field
   * @param {any} value
   */
  async function handleQuickEdit(caseItem, field, value) {
    // Map frontend field names to form state field names
    const fieldMapping = {
      subject: 'title',
      caseType: 'caseType',
      priority: 'priority',
      status: 'status',
      dueDate: 'dueDate',
      dueTime: 'dueTime',
      closedOn: 'closedOn'
    };

    // Populate form state with current case data
    const currentState = caseToFormState(caseItem);

    // Update the specific field (use mapped name if exists)
    const formField = fieldMapping[field] || field;
    currentState[formField] = value;

    // Copy to form state
    Object.assign(formState, currentState);

    await tick();
    updateForm.requestSubmit();
  }

  /**
   * Handle row change from CrmTable (inline editing)
   * @param {any} row
   * @param {string} field
   * @param {any} value
   */
  async function handleRowChange(row, field, value) {
    await handleQuickEdit(row, field, value);
  }

  /**
   * Handle view mode change
   * @param {'list' | 'kanban'} mode
   */
  async function updateViewMode(mode) {
    pageLoading = true;
    viewMode = mode;
    const url = new URL($page.url);
    if (mode === 'list') {
      url.searchParams.delete('view');
    } else {
      url.searchParams.set('view', mode);
    }
    await goto(url.toString(), { replaceState: true, noScroll: true });
    pageLoading = false;
  }

  /**
   * Handle kanban status change (drag-drop)
   * @param {string} caseId
   * @param {string} targetColumnId
   * @param {string} _columnId
   */
  async function handleKanbanStatusChange(caseId, targetColumnId, _columnId) {
    kanbanFormState.caseId = caseId;
    kanbanFormState.aboveCaseId = '';
    kanbanFormState.belowCaseId = '';

    // Determine mode from kanban data
    // In status-based mode, column.id is a status value (e.g., "New", "Assigned")
    // In pipeline-based mode, column.id is a stage UUID
    if (kanbanData?.mode === 'pipeline') {
      kanbanFormState.status = '';
      kanbanFormState.stageId = targetColumnId;
    } else {
      kanbanFormState.status = targetColumnId;
      kanbanFormState.stageId = '';
    }

    await tick();
    moveCaseForm.requestSubmit();
  }

  /**
   * Handle kanban card click (open drawer)
   * @param {any} caseItem
   */
  function handleKanbanCardClick(caseItem) {
    loadFormOptions();
    // Find full case data and open drawer
    const fullCase = casesData.find((c) => c.id === caseItem.id);
    if (fullCase) {
      drawer.openDetail(fullCase);
    } else {
      // Use kanban card data directly
      drawer.openDetail({
        id: caseItem.id,
        subject: caseItem.name,
        status: caseItem.status,
        priority: caseItem.priority,
        caseType: caseItem.case_type,
        account: caseItem.account_name ? { name: caseItem.account_name } : null,
        assignedTo: caseItem.assigned_to || []
      });
    }
  }
</script>

<svelte:head>
  <title>Chamados - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Chamados" subtitle="{filteredCases.length} de {casesData.length} chamados">
  {#snippet actions()}
    <div class="flex items-center gap-2">
      <!-- View Mode Toggle — icon-only below md -->
      <div class="border-input bg-background inline-flex rounded-lg border p-1">
        <Button
          variant={viewMode === 'list' ? 'secondary' : 'ghost'}
          size="sm"
          onclick={() => updateViewMode('list')}
          class="h-8 px-2 md:px-3"
          title="Lista"
        >
          <List class="h-4 w-4 md:mr-1.5" />
          <span class="hidden md:inline">Lista</span>
        </Button>
        <Button
          variant={viewMode === 'kanban' ? 'secondary' : 'ghost'}
          size="sm"
          onclick={() => updateViewMode('kanban')}
          class="h-8 px-2 md:px-3"
          title="Quadro"
        >
          <Columns class="h-4 w-4 md:mr-1.5" />
          <span class="hidden md:inline">Quadro</span>
        </Button>
        <Button
          variant={viewMode === 'workload' ? 'secondary' : 'ghost'}
          size="sm"
          onclick={() => updateViewMode('workload')}
          class="h-8 px-2 md:px-3"
          title="Equipe"
        >
          <BarChart3 class="h-4 w-4 md:mr-1.5" />
          <span class="hidden md:inline">Equipe</span>
        </Button>
      </div>

      <div class="bg-border mx-1 h-6 w-px"></div>

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

      <DropdownMenu.Root>
        <DropdownMenu.Trigger>
          {#snippet child({ props })}
            <Button {...props} variant="outline" size="sm" class="gap-2">
              <Eye class="h-4 w-4" />
              Colunas
              {#if columnCounts.visible < columnCounts.total}
                <span
                  class="rounded-full bg-[var(--color-primary-light)] px-1.5 py-0.5 text-xs font-medium text-[var(--color-primary-default)]"
                >
                  {columnCounts.visible}/{columnCounts.total}
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
              checked={isColumnVisible(column.key)}
              onCheckedChange={() => toggleColumn(column.key)}
              disabled={column.canHide === false}
            >
              {column.label}
            </DropdownMenu.CheckboxItem>
          {/each}
        </DropdownMenu.Content>
      </DropdownMenu.Root>

      <Button onclick={() => {
        drawer.openCreate();
        loadFormOptions();
        if (activeCasePipelineId) {
          const pipeline = casePipelines.find(p => p.id === activeCasePipelineId);
          if (pipeline?.stages?.length) {
            formPipelineId = pipeline.id;
            formStageId = pipeline.stages.slice().sort((a, b) => a.order - b.order)[0].id;
          } else { formPipelineId = ''; formStageId = ''; }
        } else { formPipelineId = ''; formStageId = ''; }
      }}>
        <Plus class="mr-2 h-4 w-4" />
        Novo Chamado
      </Button>
    </div>
  {/snippet}
</PageHeader>

<div class="relative z-20 flex-1">
  {#if pageLoading}
    <div class="h-0.5 w-full animate-pulse rounded-full bg-primary/40"></div>
  {/if}

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
      placeholder="Buscar chamados..."
    />
    <SelectFilter
      label="Status"
      options={[
        { value: '', label: 'Todos os Status' },
        { value: 'New', label: 'Novo' },
        { value: 'Assigned', label: 'Atribuído' },
        { value: 'Pending', label: 'Pendente' },
        { value: 'Closed', label: 'Fechado' },
        { value: 'Rejected', label: 'Rejeitado' },
        { value: 'Duplicate', label: 'Duplicado' },
      ]}
      value={filters.status}
      onchange={(value) => updateFilters({ ...filters, status: value, quick_filter: '' })}
    />
    <SelectFilter
      label="Prioridade"
      options={priorityFilterOptions}
      value={filters.priority}
      onchange={(value) => updateFilters({ ...filters, priority: value })}
    />
    <SelectFilter
      label="Tipo"
      options={typeFilterOptions}
      value={filters.case_type}
      onchange={(value) => updateFilters({ ...filters, case_type: value })}
    />
    <DateRangeFilter
      label="Criado"
      startDate={filters.created_at_gte}
      endDate={filters.created_at_lte}
      onchange={(start, end) =>
        updateFilters({ ...filters, created_at_gte: start, created_at_lte: end })}
    />
    <TagFilter
      tags={allTags}
      value={filters.tags}
      onchange={(ids) => updateFilters({ ...filters, tags: ids })}
    />
  </FilterBar>

  <!-- SLA Dashboard KPI Bar -->
  {#if slaDashboard && !slaDashboardLoading}
    <div class={cn(
      'mb-3 flex flex-wrap items-center gap-4 rounded-lg border px-4 py-2.5 text-sm',
      slaStatusColor === 'rose' ? 'border-rose-500/30 bg-rose-50 dark:bg-rose-500/5' :
      slaStatusColor === 'amber' ? 'border-amber-500/30 bg-amber-50 dark:bg-amber-500/5' :
      'border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/5'
    )}>
      <div class="flex items-center gap-1.5">
        <Briefcase class="h-4 w-4 text-muted-foreground" />
        <span class="font-medium text-foreground">{slaDashboard.total_open} abertos</span>
      </div>
      <div class="h-4 w-px bg-border"></div>
      <div class="flex items-center gap-1.5">
        <Timer class={cn('h-4 w-4', slaDashboard.sla_breached_count > 0 ? 'text-rose-500' : 'text-muted-foreground')} />
        <span class={slaDashboard.sla_breached_count > 0 ? 'font-semibold text-rose-600 dark:text-rose-400' : 'text-muted-foreground'}>
          {slaDashboard.sla_breached_count} SLA violado
        </span>
      </div>
      <div class="h-4 w-px bg-border"></div>
      <div class="flex items-center gap-1.5">
        <AlertTriangle class={cn('h-4 w-4', slaDashboard.sla_at_risk_count > 0 ? 'text-amber-500' : 'text-muted-foreground')} />
        <span class={slaDashboard.sla_at_risk_count > 0 ? 'font-semibold text-amber-600 dark:text-amber-400' : 'text-muted-foreground'}>
          {slaDashboard.sla_at_risk_count} em risco
        </span>
      </div>
      {#if slaDashboard.avg_resolution_hours != null}
        <div class="h-4 w-px bg-border"></div>
        <div class="flex items-center gap-1.5 text-muted-foreground">
          <Clock class="h-4 w-4" />
          <span>Resolução: {slaDashboard.avg_resolution_hours.toFixed(1)}h</span>
        </div>
      {/if}
      {#if slaDashboard.escalated_count > 0}
        <div class="h-4 w-px bg-border"></div>
        <div class="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
          <span class="font-medium">{slaDashboard.escalated_count} escalonados</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Unified filter chips (status + date shortcuts) -->
  <div class="flex items-center gap-1.5 overflow-x-auto px-4 pb-4" style="-ms-overflow-style:none;scrollbar-width:none">
    {#each quickFilterOptions as option, i}
      {#if i === 3}
        <div class="mx-0.5 h-4 w-px shrink-0 bg-border"></div>
      {/if}
      {@const isActive = activeQuickFilter === option.value}
      {@const count = chipCounts[option.value] ?? 0}
      <button
        type="button"
        class={cn(
          'inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-medium transition-colors',
          isActive
            ? option.color === 'rose' ? 'bg-rose-100 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800'
              : option.color === 'amber' ? 'bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800'
              : option.color === 'emerald' ? 'bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800'
              : option.color === 'blue' ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800'
              : 'bg-primary text-primary-foreground border-primary'
            : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground'
        )}
        onclick={() => setQuickFilter(option.value)}
      >
        {#if option.value === 'open'}
          <CircleDot class="h-3 w-3" />
        {:else if option.value === 'closed'}
          <CheckCircle2 class="h-3 w-3" />
        {:else if option.value === 'overdue'}
          <AlertTriangle class="h-3 w-3" />
        {:else if option.value === 'due_today'}
          <Clock class="h-3 w-3" />
        {:else if option.value === 'due_this_week'}
          <Calendar class="h-3 w-3" />
        {:else if option.value === 'no_date'}
          <Ban class="h-3 w-3" />
        {/if}
        {option.label}
        <span class={cn(
          'rounded-full px-1.5 text-[10px] font-semibold',
          isActive ? 'bg-black/10 dark:bg-white/15' : 'bg-muted text-muted-foreground'
        )}>
          {count}
        </span>
      </button>
    {/each}
  </div>

  {#if viewMode === 'list'}
    <CrmTable
      data={filteredCases}
      {columns}
      bind:visibleColumns
      onRowChange={handleRowChange}
      onRowClick={(row) => { loadFormOptions(); drawer.openDetail(row); }}
    >
      {#snippet emptyState()}
        <div class="flex flex-col items-center justify-center py-16 text-center">
          <div
            class="mb-4 flex size-16 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--surface-sunken)]"
          >
            <Briefcase class="size-8 text-[var(--text-tertiary)]" />
          </div>
          <h3 class="text-lg font-medium text-[var(--text-primary)]">Nenhum chamado encontrado</h3>
          <p class="mt-1 text-sm text-[var(--text-secondary)]">
            Tente ajustar seus filtros ou crie um novo chamado
          </p>
        </div>
      {/snippet}
    </CrmTable>

    <!-- Pagination (only for list view) -->
    <Pagination
      page={pagination.page}
      limit={pagination.limit}
      total={pagination.total}
      onPageChange={handlePageChange}
      onLimitChange={handleLimitChange}
    />
  {:else if viewMode === 'workload'}
    <!-- Workload View -->
    <div class="space-y-4">
      {#if caseWorkloadLoading}
        <div class="flex items-center justify-center py-16">
          <div class="text-muted-foreground text-sm">Carregando...</div>
        </div>
      {:else if caseWorkloadData && caseWorkloadData.length > 0}
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {#each caseWorkloadData as member (member.user.id)}
            {@const total = member.counts.total || 0}
            {@const breached = member.counts.sla_breached || 0}
            {@const resolved = member.counts.resolved_this_period || 0}
            {@const load = total > 15 ? 'critical' : total > 8 ? 'high' : 'normal'}
            <Card.Root class={load === 'critical' ? 'border-rose-500/30' : load === 'high' ? 'border-amber-500/30' : ''}>
              <Card.Content class="p-4">
                <div class="flex items-center gap-3 mb-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 text-sm font-semibold text-white">
                    {(member.user.name || member.user.email || '?').charAt(0).toUpperCase()}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sm text-foreground truncate">{member.user.name || member.user.email}</div>
                    <div class="text-xs text-muted-foreground">{total} chamado{total !== 1 ? 's' : ''} aberto{total !== 1 ? 's' : ''}</div>
                  </div>
                  <span class={cn(
                    'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                    load === 'critical' ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400' :
                    load === 'high' ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400' :
                    'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                  )}>
                    {load === 'critical' ? 'Crítica' : load === 'high' ? 'Alta' : 'Normal'}
                  </span>
                </div>
                <!-- Stacked bar -->
                <div class="h-3 w-full rounded-full bg-muted overflow-hidden flex">
                  {#if member.counts.open}
                    <div class="h-full bg-blue-500" style="width: {(member.counts.open / Math.max(total, 1)) * 100}%" title="Abertos: {member.counts.open}"></div>
                  {/if}
                  {#if member.counts.pending}
                    <div class="h-full bg-amber-500" style="width: {(member.counts.pending / Math.max(total, 1)) * 100}%" title="Pendentes: {member.counts.pending}"></div>
                  {/if}
                  {#if breached}
                    <div class="h-full bg-rose-500" style="width: {(breached / Math.max(total, 1)) * 100}%" title="SLA violado: {breached}"></div>
                  {/if}
                </div>
                <div class="flex items-center justify-between mt-2 text-[10px] text-muted-foreground">
                  <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-blue-500 inline-block"></span> Abertos {member.counts.open || 0}</span>
                  <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-amber-500 inline-block"></span> Pendentes {member.counts.pending || 0}</span>
                  <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-rose-500 inline-block"></span> SLA {breached}</span>
                  <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span> Resolvidos {resolved}</span>
                </div>
              </Card.Content>
            </Card.Root>
          {/each}
        </div>
      {:else}
        <Card.Root>
          <Card.Content class="py-16 text-center">
            <Users class="text-muted-foreground/50 mx-auto mb-4 h-12 w-12" />
            <p class="text-muted-foreground text-sm">Nenhum dado de carga disponível</p>
          </Card.Content>
        </Card.Root>
      {/if}
    </div>
  {:else}
    <div class="mb-4">
      <PipelineManager
        pipelines={casePipelines}
        activePipelineId={activeCasePipelineId}
        onSelect={handleCasePipelineSelect}
        onCreate={handleCasePipelineCreate}
        onDelete={handleCasePipelineDelete}
        onUpdate={handleCasePipelineUpdate}
        onStageCreate={handleCaseStageCreate}
        onStageUpdate={handleCaseStageUpdate}
        onStageDelete={handleCaseStageDelete}
        onStageReorder={handleCaseStageReorder}
        canManage={isCaseAdmin}
        teams={lazyFormOptions.teams || []}
        users={lazyFormOptions.users || []}
        module="cases"
      />
    </div>
    <CaseKanban
      data={kanbanData}
      loading={false}
      onStatusChange={handleKanbanStatusChange}
      onCardClick={handleKanbanCardClick}
    />
  {/if}
</div>

<!-- Case Drawer -->
<CrmDrawer
  bind:open={drawer.detailOpen}
  onOpenChange={(open) => {
    if (!open) {
      drawer.closeAll();
      if (accountFromUrl) {
        clearUrlParams();
      }
    }
  }}
  data={drawerFormData}
  columns={drawerColumns}
  titleKey="subject"
  titlePlaceholder="Título do chamado"
  headerLabel={drawer.mode === 'create' ? 'Novo Chamado' : 'Chamado'}
  onFieldChange={handleDrawerFieldChange}
  onDelete={handleDelete}
  onClose={() => drawer.closeAll()}
  loading={drawer.loading}
  mode={drawer.mode === 'create' ? 'create' : 'view'}
>
  {#snippet headerContent()}
    {#if drawer.mode === 'create'}
      <div class="space-y-1.5">
        <label class="text-sm font-medium text-muted-foreground">Contato</label>
        <ContactAutocomplete
          bind:selectedContact
          onSelect={handleContactSelected}
          placeholder="Buscar contato existente..."
        />
      </div>
    {:else if drawer.selected?.contacts?.length > 0}
      <div class="space-y-1">
        <label class="text-xs font-medium text-muted-foreground">Contato Principal</label>
        <a
          href="/contacts?view={drawer.selected.contacts[0].id}"
          class="flex items-center gap-2 rounded-md border border-[var(--border-default)] px-3 py-2 text-sm hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <User class="size-4 text-[var(--text-tertiary)]" />
          <span class="font-medium text-[var(--text-primary)]">{drawer.selected.contacts[0].name}</span>
        </a>
      </div>
    {/if}

    <!-- Pipeline / Stage selector -->
    {#if casePipelines.length > 0}
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Pipeline</label>
          <select
            class="w-full rounded-md border border-[var(--border-default)] bg-transparent px-3 py-1.5 text-sm"
            bind:value={formPipelineId}
            onchange={() => { formStageId = ''; }}
          >
            <option value="">Nenhum</option>
            {#each casePipelines as pipeline}
              <option value={pipeline.id}>{pipeline.name}</option>
            {/each}
          </select>
        </div>
        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Estágio</label>
          <select
            class="w-full rounded-md border border-[var(--border-default)] bg-transparent px-3 py-1.5 text-sm"
            bind:value={formStageId}
            disabled={!formPipelineId}
          >
            <option value="">Selecione...</option>
            {#each selectedPipelineStages as stage}
              <option value={stage.id}>{stage.name}</option>
            {/each}
          </select>
        </div>
      </div>
    {/if}
  {/snippet}

  {#snippet activitySection()}
    {#if drawer.mode !== 'create' && drawer.selected}
      <!-- Subtasks/Checklist -->
      <div class="mb-4">
        <div class="mb-2 text-[13px] font-medium text-[var(--text-tertiary)]">Subtarefas</div>
        <SubtaskList
          subtasks={caseSubtasks}
          onAdd={handleAddCaseSubtask}
          onToggle={handleToggleCaseSubtask}
          onUpdate={handleUpdateCaseSubtask}
          onDelete={handleDeleteCaseSubtask}
        />
      </div>

      <div class="mb-4">
        <p class="mb-2 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
          Relacionados
        </p>
        <RelatedEntitiesPanel
          entityId={drawer.selected.id}
          entityType="case"
          sections={['tasks']}
        />
      </div>
      <div class="mt-4 border-t border-[var(--border-default)] pt-4">
        <ReminderSection
          targetType="cases.case"
          targetId={drawer.selected.id}
          moduleKey="cases"
          dateFieldLabel="SLA"
        />
      </div>
      <div class="mt-4 border-t border-[var(--border-default)] pt-4">
        <EntityRunsHistory targetType="cases.case" targetId={drawer.selected.id} />
      </div>
      <CommentSection
        entityId={drawer.selected.id}
        entityType="cases"
        initialComments={drawer.selected.comments || []}
        currentUserEmail={currentUser?.email}
        isAdmin={currentUser?.organizations?.some((o) => o.role === 'ADMIN')}
      />
    {/if}
  {/snippet}

  {#snippet footerActions()}
    {#if drawer.mode !== 'create' && drawer.selected}
      {#if drawerFormData.status === 'Closed'}
        <Button variant="outline" onclick={handleReopen} disabled={isSubmitting}>Reabrir</Button>
      {:else}
        <Button variant="outline" onclick={handleClose} disabled={isSubmitting}>Fechar Chamado</Button>
      {/if}
    {/if}
    <Button variant="outline" onclick={() => drawer.closeAll()} disabled={isSubmitting}>
      Cancelar
    </Button>
    {#if isDrawerDirty || drawer.mode === 'create'}
      <Button onclick={handleSave} disabled={isSubmitting}>
        {#if isSubmitting}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
          {drawer.mode === 'create' ? 'Criando...' : 'Salvando...'}
        {:else}
          {drawer.mode === 'create' ? 'Criar Chamado' : 'Salvar Alterações'}
        {/if}
      </Button>
    {/if}
  {/snippet}
</CrmDrawer>

<!-- Hidden forms for server actions -->
<form
  method="POST"
  action="?/create"
  bind:this={createForm}
  use:enhance={createEnhanceHandler('Chamado criado com sucesso')}
  class="hidden"
>
  <input type="hidden" name="title" value={formState.title} />
  <input type="hidden" name="description" value={formState.description} />
  <input type="hidden" name="accountId" value={formState.accountId} />
  <input type="hidden" name="assignedTo" value={JSON.stringify(formState.assignedTo)} />
  <input type="hidden" name="contacts" value={JSON.stringify(formState.contacts)} />
  <input type="hidden" name="teams" value={JSON.stringify(formState.teams)} />
  <input type="hidden" name="tags" value={JSON.stringify(formState.tags)} />
  <input type="hidden" name="priority" value={formState.priority} />
  <input type="hidden" name="caseType" value={formState.caseType} />
  <input type="hidden" name="dueDate" value={formState.dueDate} />
  <input type="hidden" name="dueTime" value={formState.dueTime} />
  <input type="hidden" name="closedOn" value={formState.closedOn} />
  <input type="hidden" name="stageId" value={formStageId} />
</form>

<form
  method="POST"
  action="?/update"
  bind:this={updateForm}
  use:enhance={createEnhanceHandler('Chamado atualizado com sucesso')}
  class="hidden"
>
  <input type="hidden" name="caseId" value={formState.caseId} />
  <input type="hidden" name="title" value={formState.title} />
  <input type="hidden" name="description" value={formState.description} />
  <input type="hidden" name="assignedTo" value={JSON.stringify(formState.assignedTo)} />
  <input type="hidden" name="contacts" value={JSON.stringify(formState.contacts)} />
  <input type="hidden" name="teams" value={JSON.stringify(formState.teams)} />
  <input type="hidden" name="tags" value={JSON.stringify(formState.tags)} />
  <input type="hidden" name="priority" value={formState.priority} />
  <input type="hidden" name="caseType" value={formState.caseType} />
  <input type="hidden" name="status" value={formState.status} />
  <input type="hidden" name="dueDate" value={formState.dueDate} />
  <input type="hidden" name="dueTime" value={formState.dueTime} />
  <input type="hidden" name="closedOn" value={formState.closedOn} />
  <input type="hidden" name="stageId" value={formStageId} />
</form>

<form
  method="POST"
  action="?/delete"
  bind:this={deleteForm}
  use:enhance={createEnhanceHandler('Chamado excluído com sucesso', true)}
  class="hidden"
>
  <input type="hidden" name="caseId" value={formState.caseId} />
</form>

<form
  method="POST"
  action="?/close"
  bind:this={closeForm}
  use:enhance={createEnhanceHandler('Chamado fechado com sucesso')}
  class="hidden"
>
  <input type="hidden" name="caseId" value={formState.caseId} />
</form>

<form
  method="POST"
  action="?/reopen"
  bind:this={reopenForm}
  use:enhance={createEnhanceHandler('Chamado reaberto com sucesso')}
  class="hidden"
>
  <input type="hidden" name="caseId" value={formState.caseId} />
</form>

<form
  method="POST"
  action="?/moveCase"
  bind:this={moveCaseForm}
  use:enhance={createEnhanceHandler('Chamado movido com sucesso', false)}
  class="hidden"
>
  <input type="hidden" name="caseId" value={kanbanFormState.caseId} />
  <input type="hidden" name="status" value={kanbanFormState.status} />
  <input type="hidden" name="stageId" value={kanbanFormState.stageId} />
  <input type="hidden" name="aboveCaseId" value={kanbanFormState.aboveCaseId} />
  <input type="hidden" name="belowCaseId" value={kanbanFormState.belowCaseId} />
</form>
