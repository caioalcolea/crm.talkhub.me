<script>
  import { enhance, deserialize } from '$app/forms';
  import { invalidateAll, goto } from '$app/navigation';
  import { tick, onMount } from 'svelte';
  import { toast } from 'svelte-sonner';
  import {
    Plus,
    Phone,
    Mail,
    Building2,
    User,
    Calendar,
    Eye,
    Star,
    Globe,
    Briefcase,
    Linkedin,
    Target,
    DollarSign,
    Percent,
    MapPin,
    FileText,
    Users,
    UserPlus,
    Tag,
    MessageSquare,
    Loader2,
    ArrowRightCircle,
    Banknote,
    Filter,
    CircleDot,
    XCircle,
    ArrowRightLeft,
    Clock,
    AlertTriangle
  } from '@lucide/svelte';
  import { page } from '$app/stores';
  import {
    FilterBar,
    SearchInput,
    SelectFilter,
    DateRangeFilter,
    TagFilter
  } from '$lib/components/ui/filter';
  import { Pagination } from '$lib/components/ui/pagination';
  import { Button } from '$lib/components/ui/button/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { INDUSTRIES } from '$lib/constants/lead-choices.js';
  import { COUNTRIES } from '$lib/constants/countries.js';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
  import { formatRelativeDate, formatDate, getNameInitials } from '$lib/utils/formatting.js';
  import {
    leadStatusOptions,
    leadRatingOptions,
    getOptionStyle,
    getOptionLabel,
    getOptionBgColor
  } from '$lib/utils/table-helpers.js';
  import CrmTable from '$lib/components/ui/crm-table/CrmTable.svelte';
  import CrmDrawer from '$lib/components/ui/crm-drawer/CrmDrawer.svelte';
  import { CommentSection } from '$lib/components/ui/comment-section';
  import ReminderSection from '$lib/components/assistant/ReminderSection.svelte';
  import EntityRunsHistory from '$lib/components/assistant/EntityRunsHistory.svelte';
  import { RelatedEntitiesPanel } from '$lib/components/ui/related-entities/index.js';
  import ContactAutocomplete from '$lib/components/contacts/ContactAutocomplete.svelte';
  import { apiRequest } from '$lib/api.js';
  import { browser } from '$app/environment';
  import { orgSettings } from '$lib/stores/org.js';
  import { fetchAddressByCep } from '$lib/utils/viacep.js';
  import { ViewToggle } from '$lib/components/ui/view-toggle';
  import { LeadKanban } from '$lib/components/ui/lead-kanban';
  import { PipelineManager } from '$lib/components/ui/pipeline-manager';
  import { apiRequest as clientApiRequest } from '$lib/api.js';

  // Column visibility configuration
  const STORAGE_KEY = 'leads-column-config';

  /**
   * @typedef {'text' | 'email' | 'number' | 'date' | 'select' | 'checkbox' | 'relation'} ColumnType
   * @typedef {{ key: string, label: string, type?: ColumnType, width?: string, editable?: boolean, canHide?: boolean, getValue?: (row: any) => any, emptyText?: string, relationIcon?: string, options?: any[] }} ColumnDef
   */

  /** @type {ColumnDef[]} */
  const columns = [
    {
      key: 'title',
      label: 'Título',
      type: 'text',
      width: 'w-[200px]',
      canHide: false,
      emptyText: 'Sem título'
    },
    {
      key: 'name',
      label: 'Nome',
      type: 'text',
      width: 'w-[180px]',
      editable: false,
      canHide: true,
      getValue: (row) => `${row.firstName || ''} ${row.lastName || ''}`.trim(),
      emptyText: ''
    },
    {
      key: 'company',
      label: 'Empresa',
      type: 'relation',
      width: 'w-40',
      relationIcon: 'building',
      getValue: (row) => (typeof row.company === 'object' ? row.company?.name : row.company),
      emptyText: ''
    },
    {
      key: 'email',
      label: 'E-mail',
      type: 'email',
      width: 'w-52',
      emptyText: ''
    },
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      width: 'w-36',
      options: leadStatusOptions
    },
    {
      key: 'rating',
      label: 'Temperatura',
      type: 'select',
      width: 'w-28',
      options: leadRatingOptions
    },
    {
      key: 'createdAt',
      label: 'Criado',
      type: 'date',
      width: 'w-36',
      editable: false
    },
    // Hidden by default
    {
      key: 'phone',
      label: 'Telefone',
      type: 'text',
      width: 'w-36',
      canHide: true,
      emptyText: ''
    },
    {
      key: 'jobTitle',
      label: 'Cargo',
      type: 'text',
      width: 'w-36',
      canHide: true,
      emptyText: ''
    },
    {
      key: 'leadSource',
      label: 'Origem',
      type: 'select',
      width: 'w-28',
      canHide: true
    },
    {
      key: 'industry',
      label: 'Setor',
      type: 'select',
      width: 'w-32',
      canHide: true,
      options: INDUSTRIES.map((i) => ({
        ...i,
        color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
      }))
    },
    {
      key: 'owner',
      label: 'Atribuído',
      type: 'relation',
      width: 'w-36',
      canHide: true,
      relationIcon: 'user',
      getValue: (row) => row.owner?.name || '',
      emptyText: ''
    }
  ];

  // Default visible columns (7 columns: Title, Name, Company, Email, Status, Rating, Created)
  const DEFAULT_VISIBLE_COLUMNS = [
    'title',
    'name',
    'company',
    'email',
    'status',
    'rating',
    'createdAt'
  ];
  let visibleColumns = $state([...DEFAULT_VISIBLE_COLUMNS]);

  // Source options for leads - using design system tokens
  const sourceOptions = [
    {
      value: 'call',
      label: 'Ligação',
      color:
        'bg-[var(--activity-call)]/10 text-[var(--activity-call)] dark:bg-[var(--activity-call)]/15'
    },
    {
      value: 'email',
      label: 'E-mail',
      color:
        'bg-[var(--activity-email)]/10 text-[var(--activity-email)] dark:bg-[var(--activity-email)]/15'
    },
    {
      value: 'existing customer',
      label: 'Cliente Existente',
      color:
        'bg-[var(--color-success-light)] text-[var(--color-success-default)] dark:bg-[var(--color-success-default)]/15'
    },
    {
      value: 'partner',
      label: 'Parceiro',
      color:
        'bg-[var(--color-primary-light)] text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15'
    },
    {
      value: 'public relations',
      label: 'Relações Públicas',
      color:
        'bg-[var(--activity-meeting)]/10 text-[var(--activity-meeting)] dark:bg-[var(--activity-meeting)]/15'
    },
    {
      value: 'campaign',
      label: 'Campanha',
      color:
        'bg-[var(--stage-qualified)]/10 text-[var(--stage-qualified)] dark:bg-[var(--stage-qualified)]/15'
    },
    {
      value: 'other',
      label: 'Outro',
      color:
        'bg-[var(--surface-sunken)] text-[var(--text-secondary)] dark:bg-[var(--surface-sunken)]'
    }
  ];

  // Salutation options - using design system tokens
  const salutationOptions = [
    {
      value: 'Mr',
      label: 'Sr.',
      color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
    },
    {
      value: 'Mrs',
      label: 'Sra.',
      color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
    },
    {
      value: 'Ms',
      label: 'Srta.',
      color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
    },
    {
      value: 'Dr',
      label: 'Dr',
      color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
    },
    {
      value: 'Prof',
      label: 'Prof',
      color: 'bg-[var(--surface-sunken)] text-[var(--text-secondary)]'
    }
  ];

  // Currency options for combobox (id/name format)
  let localCurrencies = $state(/** @type {{ id: string, name: string }[]} */ ([]));
  const allCurrencyOptions = $derived([
    ...CURRENCY_CODES.filter((c) => c.value).map((c) => ({ id: c.value, name: c.label })),
    ...localCurrencies
  ]);

  function handleCreateCurrency(/** @type {string} */ name) {
    const code = name.split(' ')[0].toUpperCase();
    localCurrencies = [...localCurrencies, { id: code, name: name.includes('-') ? name : `${code} - ${name}` }];
    createFormData = { ...createFormData, currency: code };
    toast.success(`Moeda "${code}" adicionada`);
  }

  /**
   * Handle creating a new company from the company combobox.
   * Adds to the local autocomplete list and sets the company name on the form.
   * The Django lead model stores company as a free-text field (company_name),
   * so we just store the name string — no account FK needed.
   * @param {string} name
   */
  function handleCreateCompany(/** @type {string} */ name) {
    const trimmed = name.trim();
    if (!trimmed) return;
    // Add to local autocomplete list so the option is immediately selectable
    formOptions = {
      ...formOptions,
      accountsList: [
        ...formOptions.accountsList.filter((a) => a.id !== trimmed),
        { id: trimmed, name: trimmed }
      ]
    };
    // Set value in whichever form data is active
    handleDrawerFieldChange('company', trimmed);
    toast.success(`Empresa "${trimmed}" adicionada`);
  }

  // Full drawer columns for NotionDrawer (all lead fields)
  // Using $derived so currency symbol updates with org settings
  const drawerColumns = $derived([
    // Contact Information
    {
      key: 'salutation',
      label: 'Tratamento',
      type: 'select',
      icon: User,
      options: salutationOptions
    },
    {
      key: 'firstName',
      label: 'Nome',
      type: 'text',
      icon: User,
      placeholder: 'Nome',
      essential: true
    },
    {
      key: 'lastName',
      label: 'Sobrenome',
      type: 'text',
      icon: User,
      placeholder: 'Sobrenome',
      essential: true
    },
    {
      key: 'email',
      label: 'E-mail',
      type: 'email',
      icon: Mail,
      placeholder: 'Adicionar e-mail',
      essential: true
    },
    {
      key: 'phone',
      label: 'Telefone',
      type: 'text',
      icon: Phone,
      placeholder: 'Adicionar telefone',
      essential: true
    },
    {
      key: 'jobTitle',
      label: 'Cargo',
      type: 'text',
      icon: Briefcase,
      placeholder: 'Adicionar cargo'
    },
    {
      key: 'company',
      label: 'Empresa',
      type: 'combobox',
      icon: Building2,
      getValue: (/** @type {any} */ row) =>
        typeof row.company === 'object' ? row.company?.name : row.company,
      placeholder: 'Buscar ou criar empresa...',
      emptyText: 'Nenhuma empresa cadastrada'
      // essential: false — campo opcional (pessoa física não precisa de empresa)
      // options e onCreate são injetados via drawerColumnsWithOptions
    },
    {
      key: 'website',
      label: 'Site',
      type: 'text',
      icon: Globe,
      placeholder: 'Adicionar site'
    },
    {
      key: 'linkedinUrl',
      label: 'LinkedIn',
      type: 'text',
      icon: Linkedin,
      placeholder: 'Adicionar URL do LinkedIn'
    },
    // Lead Details
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      icon: Briefcase,
      options: leadStatusOptions,
      essential: true
    },
    {
      key: 'rating',
      label: 'Temperatura',
      type: 'select',
      icon: Star,
      options: leadRatingOptions
    },
    // Metadata
    {
      key: 'createdAt',
      label: 'Criado',
      type: 'date',
      icon: Calendar,
      editable: false,
      hideOnCreate: true
    },
    {
      key: 'leadSource',
      label: 'Origem',
      type: 'select',
      icon: Target,
      options: sourceOptions
    },
    {
      key: 'industry',
      label: 'Setor',
      type: 'select',
      icon: Building2,
      options: INDUSTRIES.map((i) => ({
        ...i,
        color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
      }))
    },
    // Deal Information
    {
      key: 'opportunityAmount',
      label: 'Valor do Negócio',
      type: 'number',
      icon: DollarSign,
      placeholder: '0',
      essential: true
    },
    {
      key: 'currency',
      label: 'Moeda',
      type: 'combobox',
      icon: Banknote,
      options: allCurrencyOptions,
      placeholder: 'Buscar moeda...',
      onCreate: handleCreateCurrency,
      essential: true
    },
    {
      key: 'probability',
      label: 'Probabilidade',
      type: 'number',
      icon: Percent,
      placeholder: '0-100'
    },
    {
      key: 'closeDate',
      label: 'Data de Fechamento',
      type: 'date',
      icon: Calendar,
      placeholder: 'Definir data',
      hideOnCreate: true
    },
    // Activity
    {
      key: 'lastContacted',
      label: 'Último Contato',
      type: 'date',
      icon: Calendar,
      placeholder: 'Definir data',
      hideOnCreate: true
    },
    {
      key: 'nextFollowUp',
      label: 'Próximo Follow-up',
      type: 'date',
      icon: Calendar,
      placeholder: 'Definir data'
    },
    // Address
    {
      key: 'addressLine',
      label: 'Endereço',
      type: 'text',
      icon: MapPin,
      placeholder: 'Endereço'
    },
    {
      key: 'city',
      label: 'Cidade',
      type: 'text',
      icon: MapPin,
      placeholder: 'Cidade'
    },
    {
      key: 'state',
      label: 'Estado',
      type: 'text',
      icon: MapPin,
      placeholder: 'Estado/Província'
    },
    {
      key: 'postcode',
      label: 'CEP',
      type: 'text',
      icon: MapPin,
      placeholder: 'CEP'
    },
    {
      key: 'country',
      label: 'País',
      type: 'combobox',
      icon: Globe,
      options: COUNTRIES.map((c) => ({ id: c.code, name: c.name })),
      placeholder: 'Buscar país...',
      essential: true
    },
    // Notes
    {
      key: 'description',
      label: 'Observações',
      type: 'textarea',
      icon: FileText,
      placeholder: 'Adicionar observações...'
    },
    // Assignment (multi-select fields - options populated dynamically)
    {
      key: 'assignedTo',
      label: 'Atribuído a',
      type: 'multiselect',
      icon: Users,
      options: []
    },
    {
      key: 'teams',
      label: 'Equipes',
      type: 'multiselect',
      icon: Users,
      options: []
    },
    {
      key: 'contacts',
      label: 'Contatos',
      type: 'multiselect',
      icon: UserPlus,
      options: []
    },
    {
      key: 'tags',
      label: 'Tags',
      type: 'multiselect',
      icon: Tag,
      options: []
    }
  ]);

  /**
   * Load column visibility from localStorage
   */
  function loadColumnVisibility() {
    if (typeof window === 'undefined') return;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Filter to only include valid column keys
        visibleColumns = parsed.filter((key) => columns.some((c) => c.key === key));
      }
    } catch (e) {
      console.error('Failed to load column visibility:', e);
    }
  }

  onMount(() => {
    loadColumnVisibility();
  });

  // Save to localStorage when column visibility changes
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

  /** @type {{ data: any }} */
  let { data } = $props();

  // Computed values
  const leads = $derived(data.leads || []);
  const pagination = $derived(data.pagination || { page: 1, limit: 10, total: 0, totalPages: 0 });
  const viewMode = $derived(data.viewMode || 'kanban');
  const kanbanData = $derived(data.kanbanData || null);
  const leadPipelines = $derived(data.pipelines || []);
  let activePipelineId = $state('');

  // Pipeline/stage form state for drawer create/edit
  let formPipelineId = $state('');
  let formStageId = $state('');
  const selectedPipelineStages = $derived(
    leadPipelines.find(p => p.id === formPipelineId)?.stages
      ?.slice().sort((a, b) => a.order - b.order) ?? []
  );

  $effect(() => {
    if (data.pipelineId) {
      const exists = leadPipelines.some(p => p.id === data.pipelineId);
      activePipelineId = exists ? data.pipelineId : (leadPipelines[0]?.id || '');
    } else if (leadPipelines.length > 0) {
      // Auto-select first pipeline when none specified
      activePipelineId = leadPipelines[0].id;
    }
  });

  async function handleLeadPipelineSelect(pipelineId) {
    activePipelineId = pipelineId;
    const url = new URL($page.url);
    if (pipelineId) {
      url.searchParams.set('pipeline_id', pipelineId);
    } else {
      url.searchParams.delete('pipeline_id');
    }
    url.searchParams.set('viewMode', 'kanban');
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  async function handleLeadPipelineCreate(pipelineData) {
    try {
      await clientApiRequest('/leads/pipelines/', {
        method: 'POST',
        body: pipelineData
      });
      toast.success('Pipeline criado');
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao criar pipeline');
      throw err;
    }
  }

  async function handleLeadPipelineDelete(pipelineId) {
    try {
      await clientApiRequest(`/leads/pipelines/${pipelineId}/`, { method: 'DELETE' });
      toast.success('Pipeline excluído');
      if (activePipelineId === pipelineId) activePipelineId = '';
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao excluir pipeline');
      throw err;
    }
  }

  async function handleLeadPipelineUpdate(pipelineId, pipelineData) {
    try {
      await clientApiRequest(`/leads/pipelines/${pipelineId}/`, {
        method: 'PUT',
        body: pipelineData
      });
      toast.success('Pipeline atualizado');
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao atualizar pipeline');
      throw err;
    }
  }

  async function handleLeadStageCreate(pipelineId, stageData) {
    try {
      await clientApiRequest(`/leads/pipelines/${pipelineId}/stages/`, {
        method: 'POST',
        body: stageData
      });
      toast.success('Estágio criado');
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao criar estágio');
      throw err;
    }
  }

  async function handleLeadStageUpdate(stageId, stageData) {
    try {
      await clientApiRequest(`/leads/stages/${stageId}/`, {
        method: 'PATCH',
        body: stageData
      });
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao atualizar estágio');
      throw err;
    }
  }

  async function handleLeadStageDelete(stageId) {
    try {
      await clientApiRequest(`/leads/stages/${stageId}/`, { method: 'DELETE' });
      toast.success('Estágio removido');
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao remover estágio');
      throw err;
    }
  }

  async function handleLeadStageReorder(pipelineId, stageOrder) {
    try {
      await clientApiRequest(`/leads/pipelines/${pipelineId}/stages/reorder/`, {
        method: 'POST',
        body: { stage_ids: stageOrder }
      });
      await invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao reordenar estágios');
      throw err;
    }
  }

  let isLeadAdmin = $derived(data.userRole === 'ADMIN');

  // Total lead count - use kanban data when in kanban mode for accurate count
  const totalLeadCount = $derived(
    viewMode === 'kanban' && kanbanData ? kanbanData.total_leads : pagination.total
  );

  // Lazy-loaded form options (only fetched when drawer opens)
  let formOptions = $state(
    /** @type {{ users: any[], teamsList: any[], contactsList: any[], tagsList: any[], accountsList: any[] }} */ ({
      users: [],
      teamsList: [],
      contactsList: [],
      tagsList: [],
      accountsList: []
    })
  );
  let formOptionsLoaded = $state(false);
  let formOptionsLoading = $state(false);

  /**
   * Load form options for drawer - uses pre-loaded server data
   */
  function loadFormOptions() {
    if (formOptionsLoaded || formOptionsLoading) return;

    formOptionsLoading = true;
    try {
      // Use pre-loaded data from server (avoids client-side auth issues)
      const serverFormOptions = data.formOptions || { users: [], teams: [], contacts: [] };

      const users = serverFormOptions.users.map((/** @type {any} */ u) => ({
        id: u.id,
        name: u.email || u.name || 'Unknown',
        email: u.email
      }));

      const teamsList = serverFormOptions.teams.map((/** @type {any} */ t) => ({
        id: t.id,
        name: t.name || 'Unknown'
      }));

      const contactsList = serverFormOptions.contacts.map((/** @type {any} */ c) => ({
        id: c.id,
        name: c.name || c.email || 'Unknown',
        email: c.email
      }));

      // Tags are already loaded in the page data
      const tagsList = (data.tags || []).map((/** @type {any} */ t) => ({
        id: t.id,
        name: t.name || 'Unknown'
      }));

      const accountsList = (serverFormOptions.accounts || []).map((/** @type {any} */ a) => ({
        id: a.id,
        name: a.name
      }));

      formOptions = { users, teamsList, contactsList, tagsList, accountsList };
      formOptionsLoaded = true;
    } catch (err) {
      console.error('Failed to load form options:', err);
    } finally {
      formOptionsLoading = false;
    }
  }

  // Drawer state (NotionDrawer for view/create)
  let drawerOpen = $state(false);
  /** @type {'view' | 'create'} */
  let drawerMode = $state(/** @type {'view' | 'create'} */ ('view'));
  /** @type {any} */
  let drawerData = $state(null);
  let drawerLoading = $state(false);
  let isSaving = $state(false);
  let currentUser = $derived(data.user ? { ...data.user, organizations: [{ role: data.userRole }] } : null);

  // ContactAutocomplete state for create mode
  /** @type {any} */
  let selectedContact = $state(null);
  let contactIdFromUrl = $state('');

  /**
   * Handle contact selection from autocomplete — fills form fields
   * @param {any} contact
   */
  function handleContactSelected(contact) {
    if (!contact) return;
    createFormData = {
      ...createFormData,
      firstName: contact.first_name || createFormData.firstName,
      lastName: contact.last_name || createFormData.lastName,
      email: contact.email || createFormData.email,
      phone: contact.phone || createFormData.phone,
      company: contact.account_name || contact.organization || createFormData.company,
      contacts: [...new Set([...(createFormData.contacts || []), contact.id])]
    };
  }

  // For create mode - temporary form data
  let createFormData = $state(
    /** @type {Record<string, any>} */ ({
      title: '',
      salutation: '',
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      jobTitle: '',
      company: '',
      website: '',
      linkedinUrl: '',
      status: 'ASSIGNED',
      rating: '',
      leadSource: '',
      industry: '',
      opportunityAmount: '',
      probability: '',
      closeDate: '',
      lastContacted: '',
      nextFollowUp: '',
      addressLine: '',
      city: '',
      state: '',
      postcode: '',
      country: '',
      description: '',
      assignedTo: [],
      teams: [],
      contacts: [],
      tags: []
    })
  );

  // Current drawer data (either selected lead or create form data)
  const currentDrawerData = $derived(drawerMode === 'create' ? createFormData : drawerData);

  // Drawer columns with dynamic options for multi-selects and comboboxes
  const drawerColumnsWithOptions = $derived(
    drawerColumns.map((col) => {
      if (col.key === 'assignedTo') return { ...col, options: formOptions.users || [] };
      if (col.key === 'teams') return { ...col, options: formOptions.teamsList || [] };
      if (col.key === 'contacts') return { ...col, options: formOptions.contactsList || [] };
      if (col.key === 'tags') return { ...col, options: formOptions.tagsList || [] };
      if (col.key === 'company') return { ...col, options: formOptions.accountsList || [], onCreate: handleCreateCompany };
      return col;
    })
  );

  // URL sync
  $effect(() => {
    const viewId = $page.url.searchParams.get('view');
    const action = $page.url.searchParams.get('action');

    if (action === 'create' && !drawerOpen) {
      const contactIdParam = $page.url.searchParams.get('contactId');
      if (contactIdParam) {
        contactIdFromUrl = contactIdParam;
      }
      drawerData = null;
      drawerMode = 'create';
      drawerOpen = true;
      // Pre-fill contact from URL — fetch contact details and fill form
      if (contactIdFromUrl) {
        createFormData = { ...createFormData, contacts: [contactIdFromUrl] };
        apiRequest(`/contacts/${contactIdFromUrl}/`).then((contact) => {
          if (contact && !contact.error) {
            selectedContact = contact;
            handleContactSelected(contact);
          }
        }).catch(() => {});
      }
      // Lazy load form options when drawer opens via URL
      loadFormOptions();
    } else if (viewId && leads.length > 0) {
      const lead = leads.find((l) => l.id === viewId);
      if (lead) {
        drawerData = lead;
        drawerMode = 'view';
        drawerOpen = true;
        // Lazy load form options when drawer opens via URL
        loadFormOptions();
      }
    }
  });

  /**
   * Update URL
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
    await goto(url.toString(), { replaceState: true, noScroll: true });
  }

  /**
   * Transform API lead data (snake_case) to frontend format (camelCase)
   * @param {any} lead - Raw lead data from API
   * @returns {any} Transformed lead data
   */
  function transformLeadData(lead) {
    return {
      id: lead.id,
      firstName: lead.first_name,
      lastName: lead.last_name,
      title: lead.title,
      salutation: lead.salutation,
      jobTitle: lead.job_title,
      company: lead.company_name,
      email: lead.email,
      phone: lead.phone,
      website: lead.website,
      linkedinUrl: lead.linkedin_url,
      status: lead.status ? lead.status.toUpperCase().replace(/ /g, '_') : 'ASSIGNED',
      leadSource: lead.source,
      industry: lead.industry,
      rating: lead.rating,
      opportunityAmount: lead.opportunity_amount,
      currency: lead.currency || null,
      probability: lead.probability,
      closeDate: lead.close_date,
      addressLine: lead.address_line,
      city: lead.city,
      state: lead.state,
      postcode: lead.postcode,
      country: lead.country,
      lastContacted: lead.last_contacted,
      nextFollowUp: lead.next_follow_up,
      description: lead.description,
      isConverted: lead.status === 'converted',
      isActive: lead.is_active,
      createdAt: lead.created_at,
      updatedAt: lead.updated_at || lead.created_at,
      owner: lead.assigned_to?.[0]
        ? {
            id: lead.assigned_to[0].id,
            name: lead.assigned_to[0].user_details?.email || 'Sem atribuição',
            email: lead.assigned_to[0].user_details?.email
          }
        : lead.created_by
          ? { id: lead.created_by.id, name: lead.created_by.email, email: lead.created_by.email }
          : null,
      assignedTo: (lead.assigned_to || []).map((/** @type {any} */ u) => u.id),
      teams: (lead.teams || []).map((/** @type {any} */ t) => t.id),
      primaryContactName: lead.primary_contact_name || null,
      primaryContactEmail: lead.primary_contact_email || null,
      primaryContactPhone: lead.primary_contact_phone || null,
      primaryContactId: lead.contacts?.[0]?.id || null,
      contacts: (lead.contacts || []).map((/** @type {any} */ c) => c.id),
      tags: (lead.tags || []).map((/** @type {any} */ t) => t.id),
      comments: lead.lead_comments || [],
      attachments: lead.lead_attachment || []
    };
  }

  /**
   * Open drawer for viewing/editing a lead
   * @param {any} lead
   * @param {boolean} [fromKanban=false] - Whether the lead data is from kanban (needs full fetch)
   */
  async function openLead(lead, fromKanban = false) {
    drawerMode = 'view';
    drawerOpen = true;
    updateUrl(lead.id, null);
    // Load form options (uses pre-loaded server data)
    loadFormOptions();

    // If from kanban, we need to fetch full lead data since kanban cards have minimal data
    if (fromKanban) {
      drawerLoading = true;
      try {
        // Use server action to fetch lead (avoids client-side auth issues)
        const formData = new FormData();
        formData.append('leadId', lead.id);

        const response = await fetch('?/getLead', {
          method: 'POST',
          body: formData
        });

        const responseText = await response.text();
        const result = deserialize(responseText);

        // SvelteKit form actions return { type: 'success'|'failure'|'error', data: {...} }
        if (result.type === 'success' && result.data?.lead) {
          drawerData = result.data.lead;
        } else if (result.type === 'failure') {
          console.error('Server action failed:', result.data);
          const errorMsg = /** @type {{ error?: string }} */ (result.data)?.error;
          throw new Error(errorMsg || 'Failed to fetch lead');
        } else if (result.type === 'error') {
          console.error('Server action error:', result.error);
          throw new Error(result.error?.message || 'Failed to fetch lead');
        } else {
          // Handle unexpected response format
          console.warn('Unexpected response format:', result);
          throw new Error('Failed to fetch lead');
        }
      } catch (err) {
        console.error('Failed to fetch lead details:', err);
        toast.error('Falha ao carregar detalhes do lead');
        // Fall back to what we have (minimal kanban data transformed)
        drawerData = {
          id: lead.id,
          title: lead.title || lead.full_name,
          company: lead.company_name,
          email: lead.email,
          rating: lead.rating,
          opportunityAmount: lead.opportunity_amount,
          currency: lead.currency,
          status: lead.status ? lead.status.toUpperCase().replace(/ /g, '_') : 'ASSIGNED'
        };
      } finally {
        drawerLoading = false;
      }
    } else {
      // Lead data is already in the correct format (from table view)
      drawerData = lead;
    }

    // Pre-populate pipeline/stage from lead data
    const stageId = drawerData?.stage;
    if (stageId) {
      const pipelineForStage = leadPipelines.find(p => p.stages?.some(s => s.id === stageId));
      formPipelineId = pipelineForStage?.id ?? '';
      formStageId = stageId;
    } else {
      formPipelineId = '';
      formStageId = '';
    }
  }

  /**
   * Open drawer for creating a new lead
   */
  function openCreate() {
    // Reset create form data
    createFormData = {
      title: '',
      salutation: '',
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      jobTitle: '',
      company: '',
      website: '',
      linkedinUrl: '',
      status: 'ASSIGNED',
      rating: '',
      leadSource: '',
      industry: '',
      opportunityAmount: '',
      probability: '',
      closeDate: '',
      lastContacted: '',
      nextFollowUp: '',
      addressLine: '',
      city: '',
      state: '',
      postcode: '',
      country: '',
      description: '',
      assignedTo: [],
      teams: [],
      contacts: contactIdFromUrl ? [contactIdFromUrl] : [],
      tags: []
    };
    drawerData = null;
    drawerMode = 'create';
    drawerOpen = true;
    selectedContact = null;
    updateUrl(null, 'create');
    // Lazy load form options when drawer opens
    loadFormOptions();

    // Auto-select active pipeline when creating from kanban
    if (activePipelineId) {
      const pipeline = leadPipelines.find(p => p.id === activePipelineId);
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
  }

  /**
   * Close drawer
   * @returns {Promise<void>}
   */
  async function closeDrawer() {
    drawerOpen = false;
    drawerData = null;
    await updateUrl(null, null);
  }

  /**
   * Change view mode (table/kanban)
   * @param {'table' | 'kanban'} mode
   */
  async function setViewMode(mode) {
    const url = new URL($page.url);
    url.searchParams.set('viewMode', mode);
    // Reset to first page when switching views
    url.searchParams.set('page', '1');
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  /**
   * Handle kanban status change (drag-drop)
   * @param {string} leadId
   * @param {string} newStatus
   * @param {string} _columnId
   */
  async function handleKanbanStatusChange(leadId, targetColumnId, _columnId) {
    kanbanFormState.leadId = leadId;
    kanbanFormState.aboveLeadId = '';
    kanbanFormState.belowLeadId = '';

    // Determine mode from kanban data
    // In status-based mode, column.id is a status value (e.g., "assigned", "in process")
    // In pipeline-based mode, column.id is a stage UUID
    if (kanbanData?.mode === 'pipeline') {
      kanbanFormState.status = '';
      kanbanFormState.stageId = targetColumnId;
    } else {
      kanbanFormState.status = targetColumnId;
      kanbanFormState.stageId = '';
    }

    await tick();
    updateStatusForm.requestSubmit();
  }

  /**
   * Handle drawer open change
   * @param {boolean} open
   */
  function handleDrawerChange(open) {
    drawerOpen = open;
    if (!open) {
      drawerData = null;
      updateUrl(null, null);
    }
  }

  /**
   * Handle row change from NotionTable (inline editing)
   * @param {any} row
   * @param {string} field
   * @param {any} value
   */
  async function handleRowChange(row, field, value) {
    await handleQuickEdit(row, field, value);
  }

  /**
   * Handle field change from CrmDrawer - just updates local state
   * @param {string} field
   * @param {any} value
   */
  async function handleDrawerFieldChange(field, value) {
    if (drawerMode === 'create') {
      // For create mode, just update the form data
      createFormData = { ...createFormData, [field]: value };
    } else if (drawerData) {
      // For edit mode, just update local data - no auto-save
      drawerData = { ...drawerData, [field]: value };
    }

    // ViaCEP: auto-fill address from CEP
    if (field === 'postcode') {
      const clean = value?.replace(/\D/g, '') || '';
      if (clean.length === 8) {
        const address = await fetchAddressByCep(clean);
        if (address) {
          if (drawerMode === 'create') {
            createFormData = { ...createFormData, ...address };
          } else if (drawerData) {
            drawerData = { ...drawerData, ...address };
          }
          toast.success('Endereço preenchido pelo CEP');
        }
      }
    }
  }

  /**
   * Handle save for view/edit mode
   */
  async function handleDrawerUpdate() {
    if (drawerMode !== 'view' || !drawerData) return;

    isSaving = true;
    // Populate form state with current drawer data
    const currentState = leadToFormState(drawerData);
    Object.assign(formState, currentState);

    await tick();
    updateForm.requestSubmit();
  }

  /**
   * Handle title change from NotionDrawer
   * @param {string} value
   */
  async function handleTitleChange(value) {
    if (drawerMode === 'create') {
      // Parse the name into firstName and lastName
      const parts = value.trim().split(' ');
      createFormData = {
        ...createFormData,
        title: value,
        firstName: parts[0] || '',
        lastName: parts.slice(1).join(' ') || ''
      };
    } else if (drawerData) {
      // For existing leads, update title
      await handleQuickEdit(drawerData, 'title', value);
    }
  }

  /**
   * Handle delete from NotionDrawer
   */
  async function handleDrawerDelete() {
    if (!drawerData) return;
    const lead = drawerData;
    closeDrawer();
    await handleRowDelete(lead);
  }

  /**
   * Handle convert from NotionDrawer
   */
  async function handleDrawerConvert() {
    if (!drawerData) return;
    formState.leadId = drawerData.id;
    await tick();
    convertForm.requestSubmit();
  }

  /**
   * Handle create new lead
   */
  async function handleCreateLead() {
    if (!createFormData.title?.trim()) {
      toast.error('O título do lead é obrigatório');
      return;
    }

    isSaving = true;
    try {
      // Populate form state
      formState.salutation = createFormData.salutation || '';
      formState.title = createFormData.title || '';
      formState.firstName = createFormData.firstName || '';
      formState.lastName = createFormData.lastName || '';
      formState.email = createFormData.email || '';
      formState.phone = createFormData.phone || '';
      formState.jobTitle = createFormData.jobTitle || '';
      formState.company = createFormData.company || '';
      formState.website = createFormData.website || '';
      formState.linkedinUrl = createFormData.linkedinUrl || '';
      formState.status = createFormData.status || 'ASSIGNED';
      formState.source = createFormData.leadSource || '';
      formState.rating = createFormData.rating || '';
      formState.industry = createFormData.industry || '';
      formState.opportunityAmount = createFormData.opportunityAmount || '';
      formState.currency = createFormData.currency || $orgSettings.default_currency || 'BRL';
      formState.probability = createFormData.probability || '';
      formState.closeDate = createFormData.closeDate || '';
      formState.lastContacted = createFormData.lastContacted || '';
      formState.nextFollowUp = createFormData.nextFollowUp || '';
      formState.addressLine = createFormData.addressLine || '';
      formState.city = createFormData.city || '';
      formState.state = createFormData.state || '';
      formState.postcode = createFormData.postcode || '';
      formState.country = createFormData.country || '';
      formState.description = createFormData.description || '';
      formState.assignedTo = createFormData.assignedTo || [];
      formState.teams = createFormData.teams || [];
      formState.contacts = createFormData.contacts || [];
      formState.tags = createFormData.tags || [];

      await tick();
      createForm.requestSubmit();
    } finally {
      isSaving = false;
    }
  }

  // URL-based filter state from server
  const filters = $derived(data.filters);
  const filterOptions = $derived(data.filterOptions);

  // Count active filters
  const activeFiltersCount = $derived.by(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.status) count++;
    if (filters.source) count++;
    if (filters.rating) count++;
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
    const url = new URL($page.url);
    // Clear existing filter params (preserve view/action)
    [
      'search',
      'status',
      'source',
      'rating',
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

  // Filter panel expansion state
  let filtersExpanded = $state(false);

  // All filtering is server-side via URL params
  const filteredLeads = $derived(leads);

  // ---- Quick filter chips (unified: status + date shortcuts) ----
  /** @type {{ value: string, label: string, color: string|null }[]} */
  const quickFilterOptions = [
    { value: '', label: 'Todos', color: null },
    { value: 'open', label: 'Abertos', color: 'blue' },
    { value: 'lost', label: 'Perdidos', color: 'rose' },
    { value: 'converted', label: 'Convertidos', color: 'emerald' },
    // separator at index 4
    { value: 'recent', label: 'Recentes (7d)', color: null },
    { value: 'stale', label: 'Sem Atividade (30d)', color: 'amber' },
    { value: 'closing_soon', label: 'Fechamento Próximo', color: null },
  ];

  const activeQuickFilter = $derived(filters.quick_filter || '');

  // Client-side counts for chip badges (approximate — from current page data)
  const chipCounts = $derived.by(() => {
    return {
      '': totalLeadCount,
      open: leads.filter((/** @type {any} */ l) => ['ASSIGNED', 'IN_PROCESS'].includes(l.status)).length,
      lost: leads.filter((/** @type {any} */ l) => ['CLOSED', 'RECYCLED'].includes(l.status)).length,
      converted: leads.filter((/** @type {any} */ l) => l.status === 'CONVERTED').length,
      recent: leads.length, // approximate
      stale: leads.length, // approximate
      closing_soon: leads.length, // approximate
    };
  });

  /**
   * Set quick filter — server-side via URL
   * @param {string} value
   */
  async function setQuickFilter(value) {
    const url = new URL($page.url);
    url.searchParams.delete('quick_filter');
    url.searchParams.delete('status');
    if (value) {
      url.searchParams.set('quick_filter', value);
    }
    url.searchParams.set('page', '1');
    await goto(url.toString(), { replaceState: true, noScroll: true, invalidateAll: true });
  }

  // Form references for server actions
  /** @type {HTMLFormElement} */
  let createForm;
  /** @type {HTMLFormElement} */
  let updateForm;
  /** @type {HTMLFormElement} */
  let deleteForm;
  /** @type {HTMLFormElement} */
  let convertForm;
  /** @type {HTMLFormElement} */
  let updateStatusForm;

  // Kanban form state (for drag-drop status updates)
  let kanbanFormState = $state({
    leadId: '',
    status: '',
    stageId: '',
    aboveLeadId: '',
    belowLeadId: ''
  });
  // Form data state
  let formState = $state({
    leadId: '',
    // Core Information
    salutation: '',
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    company: '',
    title: '',
    jobTitle: '',
    website: '',
    linkedinUrl: '',
    // Sales Pipeline
    status: '',
    source: '',
    industry: '',
    rating: '',
    opportunityAmount: '',
    currency: '',
    probability: '',
    closeDate: '',
    // Address
    addressLine: '',
    city: '',
    state: '',
    postcode: '',
    country: '',
    // Activity
    lastContacted: '',
    nextFollowUp: '',
    description: '',
    // Assignment
    ownerId: '',
    assignedTo: /** @type {string[]} */ ([]),
    teams: /** @type {string[]} */ ([]),
    contacts: /** @type {string[]} */ ([]),
    tags: /** @type {string[]} */ ([])
  });

  /**
   * Get full name
   * @param {any} lead
   */
  function getFullName(lead) {
    return `${lead.firstName} ${lead.lastName}`.trim();
  }

  /**
   * Get initials for lead
   * @param {any} lead
   */
  function getLeadInitials(lead) {
    return getNameInitials(lead.firstName, lead.lastName);
  }

  /**
   * Handle form submit from drawer
   * @param {any} formData
   */
  async function handleFormSubmit(formData) {
    // Populate form state
    // Core Information
    formState.firstName = formData.first_name || '';
    formState.lastName = formData.last_name || '';
    formState.email = formData.email || '';
    formState.phone = formData.phone || '';
    formState.company = formData.company_name || '';
    formState.title = formData.title || '';
    formState.jobTitle = formData.job_title || '';
    formState.website = formData.website || '';
    formState.linkedinUrl = formData.linkedin_url || '';
    // Sales Pipeline
    formState.status = formData.status || '';
    formState.source = formData.source || '';
    formState.industry = formData.industry || '';
    formState.rating = formData.rating || '';
    formState.opportunityAmount = formData.opportunity_amount || '';
    formState.currency = formData.currency || $orgSettings.default_currency || 'BRL';
    formState.probability = formData.probability || '';
    formState.closeDate = formData.close_date || '';
    // Address
    formState.addressLine = formData.address_line || '';
    formState.city = formData.city || '';
    formState.state = formData.state || '';
    formState.postcode = formData.postcode || '';
    formState.country = formData.country || '';
    // Activity
    formState.lastContacted = formData.last_contacted || '';
    formState.nextFollowUp = formData.next_follow_up || '';
    formState.description = formData.description || '';

    await tick();

    if (drawerMode === 'view' && drawerData) {
      // Edit mode
      formState.leadId = drawerData.id;
      // Use existing owner when editing (form doesn't have owner selection)
      formState.ownerId = drawerData.owner?.id || '';
      await tick();
      updateForm.requestSubmit();
    } else {
      // Create mode
      formState.ownerId = '';
      createForm.requestSubmit();
    }
  }

  /**
   * Handle lead delete
   */
  async function handleDelete() {
    if (!drawerData) return;
    if (!confirm(`Are you sure you want to delete ${getFullName(drawerData)}?`)) return;

    formState.leadId = drawerData.id;
    await tick();
    deleteForm.requestSubmit();
  }

  /**
   * Handle lead convert
   */
  async function handleConvert() {
    if (!drawerData) return;

    formState.leadId = drawerData.id;
    await tick();
    convertForm.requestSubmit();
  }

  /**
   * Handle lead delete from row action
   * @param {any} lead
   */
  async function handleRowDelete(lead) {
    if (!confirm(`Are you sure you want to delete ${getFullName(lead)}?`)) return;

    formState.leadId = lead.id;
    await tick();
    deleteForm.requestSubmit();
  }

  /**
   * Convert lead to form state for quick edit
   * @param {any} lead
   */
  function leadToFormState(lead) {
    return {
      leadId: lead.id,
      salutation: lead.salutation || '',
      firstName: lead.firstName || '',
      lastName: lead.lastName || '',
      email: lead.email || '',
      phone: lead.phone || '',
      company: typeof lead.company === 'object' ? lead.company?.name || '' : lead.company || '',
      title: lead.title || '',
      jobTitle: lead.jobTitle || '',
      website: lead.website || '',
      linkedinUrl: lead.linkedinUrl || '',
      status: lead.status || '',
      source: lead.leadSource || '',
      industry: lead.industry || '',
      rating: lead.rating || '',
      opportunityAmount: lead.opportunityAmount || '',
      probability: lead.probability || '',
      closeDate: lead.closeDate || '',
      addressLine: lead.addressLine || '',
      city: lead.city || '',
      state: lead.state || '',
      postcode: lead.postcode || '',
      country: lead.country || '',
      lastContacted: lead.lastContacted || '',
      nextFollowUp: lead.nextFollowUp || '',
      description: lead.description || '',
      ownerId: lead.owner?.id || '',
      assignedTo: lead.assignedTo || [],
      teams: lead.teams || [],
      contacts: lead.contacts || [],
      tags: lead.tags || []
    };
  }

  /**
   * Handle quick edit from cell
   * @param {any} lead
   * @param {string} field
   * @param {string} value
   */
  async function handleQuickEdit(lead, field, value) {
    // Populate form state with current lead data
    const currentState = leadToFormState(lead);

    // Update the specific field
    currentState[field] = value;

    // Copy to form state
    Object.assign(formState, currentState);

    await tick();
    updateForm.requestSubmit();
  }

  /**
   * Create enhance handler for form actions
   * @param {string} successMessage
   * @param {boolean} shouldCloseDrawer
   */
  function createEnhanceHandler(successMessage, shouldCloseDrawer = true) {
    return () => {
      return async ({ result }) => {
        isSaving = false;
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
</script>

<svelte:head>
  <title>Funil de Venda - TalkHub CRM</title>
</svelte:head>

<PageHeader
  title="Funil de Venda"
  subtitle="{viewMode === 'kanban'
    ? totalLeadCount
    : filteredLeads.length} de {totalLeadCount} leads"
>
  {#snippet actions()}
    <div class="flex items-center gap-2">
      <!-- View Toggle -->
      <ViewToggle view={viewMode} onchange={setViewMode} />

      <div class="mx-1 h-6 w-px bg-[var(--border-default)]"></div>

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
            class="rounded-full bg-[var(--color-primary-light)] px-1.5 py-0.5 text-xs font-medium text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15"
          >
            {activeFiltersCount}
          </span>
        {/if}
      </Button>

      <!-- Column Visibility (only for table view) -->
      {#if viewMode === 'table'}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            {#snippet child({ props })}
              <Button {...props} variant="outline" size="sm" class="gap-2">
                <Eye class="h-4 w-4" />
                Colunas
                {#if visibleColumns.length < columns.length}
                  <span
                    class="rounded-full bg-[var(--color-primary-light)] px-1.5 py-0.5 text-xs font-medium text-[var(--color-primary-default)] dark:bg-[var(--color-primary-default)]/15"
                  >
                    {visibleColumns.length}/{columns.length}
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
                disabled={column.canHide === false}
                onCheckedChange={() => toggleColumn(column.key)}
              >
                {column.label}
              </DropdownMenu.CheckboxItem>
            {/each}
          </DropdownMenu.Content>
        </DropdownMenu.Root>
      {/if}

      <Button onclick={openCreate}>
        <Plus class="mr-2 h-4 w-4" />
        Novo Lead
      </Button>
    </div>
  {/snippet}
</PageHeader>

<div class="relative z-20 flex-1">
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
      placeholder="Buscar leads..."
      showLabel={false}
      onchange={(value) => updateFilters({ ...filters, search: value })}
      class="w-64"
    />
    <SelectFilter
      label="Status"
      options={[
        { value: '', label: 'Todos os Status' },
        { value: 'assigned', label: 'Atribuído' },
        { value: 'in process', label: 'Em Andamento' },
        { value: 'converted', label: 'Convertido' },
        { value: 'recycled', label: 'Reciclado' },
        { value: 'closed', label: 'Fechado' },
      ]}
      value={filters.status}
      onchange={(value) => updateFilters({ ...filters, status: value, quick_filter: '' })}
    />
    <SelectFilter
      label="Origem"
      options={filterOptions.sources}
      value={filters.source || 'ALL'}
      onchange={(value) => updateFilters({ ...filters, source: value })}
      class="w-40"
    />
    <SelectFilter
      label="Temperatura"
      options={filterOptions.ratings}
      value={filters.rating || 'ALL'}
      onchange={(value) => updateFilters({ ...filters, rating: value })}
      class="w-32"
    />
    <DateRangeFilter
      label="Criado em"
      startDate={filters.created_at_gte}
      endDate={filters.created_at_lte}
      onchange={(start, end) =>
        updateFilters({ ...filters, created_at_gte: start, created_at_lte: end })}
      class="w-56"
    />
    <TagFilter
      tags={data.tags || []}
      value={filters.tags}
      onchange={(ids) => updateFilters({ ...filters, tags: ids })}
    />
  </FilterBar>

  <!-- Unified filter chips (status + date shortcuts) -->
  <div class="flex items-center gap-1.5 overflow-x-auto px-4 pb-4" style="-ms-overflow-style:none;scrollbar-width:none">
    {#each quickFilterOptions as option, i}
      {#if i === 4}
        <div class="mx-0.5 h-4 w-px shrink-0 bg-border"></div>
      {/if}
      {@const isActive = activeQuickFilter === option.value}
      {@const count = chipCounts[option.value] ?? 0}
      <button
        type="button"
        class="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-medium transition-colors
          {isActive
            ? option.color === 'rose' ? 'bg-rose-100 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800'
              : option.color === 'amber' ? 'bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800'
              : option.color === 'emerald' ? 'bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800'
              : option.color === 'blue' ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800'
              : 'bg-primary text-primary-foreground border-primary'
            : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground'
          }"
        onclick={() => setQuickFilter(option.value)}
      >
        {#if option.value === 'open'}
          <CircleDot class="h-3 w-3" />
        {:else if option.value === 'lost'}
          <XCircle class="h-3 w-3" />
        {:else if option.value === 'converted'}
          <ArrowRightCircle class="h-3 w-3" />
        {:else if option.value === 'recent'}
          <Clock class="h-3 w-3" />
        {:else if option.value === 'stale'}
          <AlertTriangle class="h-3 w-3" />
        {:else if option.value === 'closing_soon'}
          <Calendar class="h-3 w-3" />
        {/if}
        {option.label}
        {#if option.value === '' || option.value === 'open' || option.value === 'lost' || option.value === 'converted'}
          <span class="rounded-full px-1.5 text-[10px] font-semibold
            {isActive ? 'bg-black/10 dark:bg-white/15' : 'bg-muted text-muted-foreground'}">
            {count}
          </span>
        {/if}
      </button>
    {/each}
  </div>

  <!-- Content: Table or Kanban -->
  {#if viewMode === 'kanban'}
    <!-- Pipeline Manager -->
    <div class="mb-4">
      <PipelineManager
        pipelines={leadPipelines}
        {activePipelineId}
        onSelect={handleLeadPipelineSelect}
        onCreate={handleLeadPipelineCreate}
        onDelete={handleLeadPipelineDelete}
        onUpdate={handleLeadPipelineUpdate}
        onStageCreate={handleLeadStageCreate}
        onStageUpdate={handleLeadStageUpdate}
        onStageDelete={handleLeadStageDelete}
        onStageReorder={handleLeadStageReorder}
        canManage={isLeadAdmin}
        teams={data.formOptions?.teams || []}
        users={data.formOptions?.users || []}
        module="leads"
      />
    </div>

    <!-- Kanban View -->
    <LeadKanban
      data={kanbanData}
      onStatusChange={handleKanbanStatusChange}
      onCardClick={(lead) => openLead(lead, true)}
    />
  {:else}
    <!-- Table View -->
    {#if filteredLeads.length === 0}
      <div class="flex flex-col items-center justify-center py-16 text-center">
        <div
          class="mb-4 flex size-16 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--surface-sunken)]"
        >
          <User class="size-8 text-[var(--text-tertiary)]" />
        </div>
        <h3 class="text-lg font-medium text-[var(--text-primary)]">Nenhum lead encontrado</h3>
        <p class="mt-1 text-sm text-[var(--text-secondary)]">Crie um novo lead para começar</p>
      </div>
    {:else}
      <!-- Desktop Table using CrmTable -->
      <div class="hidden md:block">
        <CrmTable
          data={filteredLeads}
          {columns}
          bind:visibleColumns
          onRowChange={handleRowChange}
          onRowClick={(row) => openLead(row)}
        >
          {#snippet emptyState()}
            <div class="flex flex-col items-center justify-center py-16 text-center">
              <div
                class="mb-4 flex size-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--surface-sunken)]"
              >
                <User class="size-6 text-[var(--text-tertiary)]" />
              </div>
              <h3 class="text-lg font-medium text-[var(--text-primary)]">Nenhum lead encontrado</h3>
            </div>
          {/snippet}
        </CrmTable>
      </div>

      <!-- Mobile Card View -->
      <div class="divide-y divide-[var(--border-default)]/50 md:hidden">
        {#each filteredLeads as lead (lead.id)}
          <button
            type="button"
            class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--color-primary-light)] dark:hover:bg-[var(--color-primary-default)]/5"
            onclick={() => openLead(lead)}
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-start justify-between gap-2">
                <div>
                  <p class="text-sm font-medium text-[var(--text-primary)]">
                    {getFullName(lead)}
                  </p>
                  {#if lead.company}
                    <p class="text-sm text-[var(--text-secondary)]">
                      {typeof lead.company === 'object' ? lead.company.name : lead.company}
                    </p>
                  {/if}
                </div>
                <span
                  class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium {getOptionStyle(
                    lead.status,
                    leadStatusOptions
                  )}"
                >
                  {getOptionLabel(lead.status, leadStatusOptions)}
                </span>
              </div>
              <div
                class="mt-2 flex flex-wrap items-center gap-3 text-xs text-[var(--text-secondary)]"
              >
                {#if lead.rating}
                  <span
                    class="rounded-full px-2 py-0.5 {getOptionStyle(
                      lead.rating,
                      leadRatingOptions
                    )}"
                  >
                    {getOptionLabel(lead.rating, leadRatingOptions)}
                  </span>
                {/if}
                <span>{formatRelativeDate(lead.createdAt)}</span>
              </div>
            </div>
          </button>
        {/each}

        <!-- Mobile new row button -->
        <button
          type="button"
          onclick={openCreate}
          class="flex w-full items-center gap-2 px-4 py-3 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-raised)] hover:text-[var(--text-primary)]"
        >
          <Plus class="h-4 w-4" />
          Novo
        </button>
      </div>
    {/if}

    <!-- Pagination (only for table view) -->
    <Pagination
      page={pagination.page}
      limit={pagination.limit}
      total={pagination.total}
      onPageChange={handlePageChange}
      onLimitChange={handleLimitChange}
    />
  {/if}
</div>

<!-- Lead Drawer -->
<CrmDrawer
  bind:open={drawerOpen}
  onOpenChange={handleDrawerChange}
  data={currentDrawerData}
  columns={drawerColumnsWithOptions}
  titleKey="title"
  titlePlaceholder={drawerMode === 'create' ? 'Título do Lead' : 'Lead sem título'}
  headerLabel={drawerMode === 'create' ? 'Novo Lead' : 'Lead'}
  mode={drawerMode}
  loading={drawerLoading}
  onFieldChange={handleDrawerFieldChange}
  onDelete={drawerMode !== 'create' ? handleDrawerDelete : undefined}
  onClose={closeDrawer}
>
  {#snippet headerContent()}
    {#if drawerMode === 'create'}
      <div class="space-y-1.5">
        <label class="text-sm font-medium text-muted-foreground">Contato</label>
        <ContactAutocomplete
          bind:selectedContact
          onSelect={handleContactSelected}
          placeholder="Buscar contato existente..."
        />
      </div>
    {:else if drawerData?.primaryContactName}
      <div class="space-y-1">
        <label class="text-xs font-medium text-muted-foreground">Contato Principal</label>
        <a
          href="/contacts?view={drawerData.primaryContactId}"
          class="flex items-center gap-2 rounded-md border border-[var(--border-default)] px-3 py-2 text-sm hover:bg-[var(--surface-sunken)] transition-colors"
        >
          <User class="size-4 text-[var(--text-tertiary)]" />
          <div class="flex flex-col">
            <span class="font-medium text-[var(--text-primary)]">{drawerData.primaryContactName}</span>
            {#if drawerData.primaryContactEmail}
              <span class="text-xs text-[var(--text-tertiary)]">{drawerData.primaryContactEmail}</span>
            {/if}
          </div>
        </a>
      </div>
    {/if}

    <!-- Pipeline / Stage selector -->
    {#if leadPipelines.length > 0}
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Pipeline</label>
          <select
            class="w-full rounded-md border border-[var(--border-default)] bg-transparent px-3 py-1.5 text-sm"
            bind:value={formPipelineId}
            onchange={() => { formStageId = ''; }}
          >
            <option value="">Nenhum</option>
            {#each leadPipelines as pipeline}
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
    {#if drawerMode !== 'create' && drawerData}
      <div class="mb-4">
        <p class="mb-2 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
          Relacionados
        </p>
        <RelatedEntitiesPanel
          entityId={drawerData.id}
          entityType="lead"
          sections={['opportunities', 'tasks']}
        />
      </div>
      <div class="mt-4 border-t border-[var(--border-default)] pt-4">
        <ReminderSection
          targetType="leads.lead"
          targetId={drawerData.id}
          moduleKey="leads"
          dateFieldLabel="follow-up"
        />
      </div>
      <div class="mt-4 border-t border-[var(--border-default)] pt-4">
        <EntityRunsHistory targetType="leads.lead" targetId={drawerData.id} />
      </div>
      <CommentSection
        entityId={drawerData.id}
        entityType="leads"
        initialComments={drawerData.comments || []}
        currentUserEmail={currentUser?.email}
        isAdmin={currentUser?.organizations?.some((o) => o.role === 'ADMIN')}
      />
    {/if}
  {/snippet}

  {#snippet footerActions()}
    {#if drawerMode === 'create'}
      <Button variant="outline" onclick={closeDrawer}>Cancelar</Button>
      <Button onclick={handleCreateLead} disabled={isSaving}>
        {#if isSaving}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
          Criando...
        {:else}
          Criar Lead
        {/if}
      </Button>
    {:else}
      <Button variant="outline" onclick={closeDrawer} disabled={isSaving}>Cancelar</Button>
      {#if drawerData?.status !== 'converted'}
        <Button variant="outline" onclick={handleDrawerConvert} disabled={isSaving}>
          <ArrowRightCircle class="mr-2 h-4 w-4" />
          Converter
        </Button>
      {/if}
      <Button onclick={handleDrawerUpdate} disabled={isSaving}>
        {#if isSaving}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
          Salvando...
        {:else}
          Salvar
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
  use:enhance={createEnhanceHandler('Lead criado com sucesso')}
  class="hidden"
>
  <!-- Core Information -->
  <input type="hidden" name="salutation" value={formState.salutation} />
  <input type="hidden" name="firstName" value={formState.firstName} />
  <input type="hidden" name="lastName" value={formState.lastName} />
  <input type="hidden" name="email" value={formState.email} />
  <input type="hidden" name="phone" value={formState.phone} />
  <input type="hidden" name="company" value={formState.company} />
  <input type="hidden" name="title" value={formState.title} />
  <input type="hidden" name="jobTitle" value={formState.jobTitle} />
  <input type="hidden" name="website" value={formState.website} />
  <input type="hidden" name="linkedinUrl" value={formState.linkedinUrl} />
  <!-- Sales Pipeline -->
  <input type="hidden" name="status" value={formState.status} />
  <input type="hidden" name="source" value={formState.source} />
  <input type="hidden" name="industry" value={formState.industry} />
  <input type="hidden" name="rating" value={formState.rating} />
  <input type="hidden" name="opportunityAmount" value={formState.opportunityAmount} />
  <input type="hidden" name="currency" value={formState.currency} />
  <input type="hidden" name="probability" value={formState.probability} />
  <input type="hidden" name="closeDate" value={formState.closeDate} />
  <!-- Address -->
  <input type="hidden" name="addressLine" value={formState.addressLine} />
  <input type="hidden" name="city" value={formState.city} />
  <input type="hidden" name="state" value={formState.state} />
  <input type="hidden" name="postcode" value={formState.postcode} />
  <input type="hidden" name="country" value={formState.country} />
  <!-- Activity -->
  <input type="hidden" name="lastContacted" value={formState.lastContacted} />
  <input type="hidden" name="nextFollowUp" value={formState.nextFollowUp} />
  <input type="hidden" name="description" value={formState.description} />
  <!-- Assignment -->
  <input type="hidden" name="ownerId" value={formState.ownerId} />
  <input type="hidden" name="assignedTo" value={JSON.stringify(formState.assignedTo)} />
  <input type="hidden" name="teams" value={JSON.stringify(formState.teams)} />
  <input type="hidden" name="contacts" value={JSON.stringify(formState.contacts)} />
  <input type="hidden" name="tags" value={JSON.stringify(formState.tags)} />
  <input type="hidden" name="stageId" value={formStageId} />
</form>

<form
  method="POST"
  action="?/update"
  bind:this={updateForm}
  use:enhance={createEnhanceHandler('Lead atualizado com sucesso')}
  class="hidden"
>
  <input type="hidden" name="leadId" value={formState.leadId} />
  <!-- Core Information -->
  <input type="hidden" name="salutation" value={formState.salutation} />
  <input type="hidden" name="firstName" value={formState.firstName} />
  <input type="hidden" name="lastName" value={formState.lastName} />
  <input type="hidden" name="email" value={formState.email} />
  <input type="hidden" name="phone" value={formState.phone} />
  <input type="hidden" name="company" value={formState.company} />
  <input type="hidden" name="title" value={formState.title} />
  <input type="hidden" name="jobTitle" value={formState.jobTitle} />
  <input type="hidden" name="website" value={formState.website} />
  <input type="hidden" name="linkedinUrl" value={formState.linkedinUrl} />
  <!-- Sales Pipeline -->
  <input type="hidden" name="status" value={formState.status} />
  <input type="hidden" name="source" value={formState.source} />
  <input type="hidden" name="industry" value={formState.industry} />
  <input type="hidden" name="rating" value={formState.rating} />
  <input type="hidden" name="opportunityAmount" value={formState.opportunityAmount} />
  <input type="hidden" name="currency" value={formState.currency} />
  <input type="hidden" name="probability" value={formState.probability} />
  <input type="hidden" name="closeDate" value={formState.closeDate} />
  <!-- Address -->
  <input type="hidden" name="addressLine" value={formState.addressLine} />
  <input type="hidden" name="city" value={formState.city} />
  <input type="hidden" name="state" value={formState.state} />
  <input type="hidden" name="postcode" value={formState.postcode} />
  <input type="hidden" name="country" value={formState.country} />
  <!-- Activity -->
  <input type="hidden" name="lastContacted" value={formState.lastContacted} />
  <input type="hidden" name="nextFollowUp" value={formState.nextFollowUp} />
  <input type="hidden" name="description" value={formState.description} />
  <!-- Assignment -->
  <input type="hidden" name="ownerId" value={formState.ownerId} />
  <input type="hidden" name="assignedTo" value={JSON.stringify(formState.assignedTo)} />
  <input type="hidden" name="teams" value={JSON.stringify(formState.teams)} />
  <input type="hidden" name="contacts" value={JSON.stringify(formState.contacts)} />
  <input type="hidden" name="tags" value={JSON.stringify(formState.tags)} />
  <input type="hidden" name="stageId" value={formStageId} />
</form>

<form
  method="POST"
  action="?/delete"
  bind:this={deleteForm}
  use:enhance={createEnhanceHandler('Lead excluído com sucesso')}
  class="hidden"
>
  <input type="hidden" name="leadId" value={formState.leadId} />
</form>

<form
  method="POST"
  action="?/convert"
  bind:this={convertForm}
  use:enhance={createEnhanceHandler('Lead convertido com sucesso')}
  class="hidden"
>
  <input type="hidden" name="leadId" value={formState.leadId} />
</form>

<form
  method="POST"
  action="?/updateStatus"
  bind:this={updateStatusForm}
  use:enhance={createEnhanceHandler('Status do lead atualizado com sucesso', false)}
  class="hidden"
>
  <input type="hidden" name="leadId" value={kanbanFormState.leadId} />
  <input type="hidden" name="status" value={kanbanFormState.status} />
  <input type="hidden" name="stageId" value={kanbanFormState.stageId} />
  <input type="hidden" name="aboveLeadId" value={kanbanFormState.aboveLeadId} />
  <input type="hidden" name="belowLeadId" value={kanbanFormState.belowLeadId} />
</form>
