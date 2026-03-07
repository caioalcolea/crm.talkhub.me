<script>
  import { Search, UserPlus, Loader2, Building2, Mail, Phone, X } from '@lucide/svelte';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { toast } from 'svelte-sonner';

  /**
   * @type {{
   *   onSelect?: (contact: any) => void,
   *   onCreate?: (contact: any) => void,
   *   placeholder?: string,
   *   required?: boolean,
   *   selectedContact?: any,
   *   class?: string
   * }}
   */
  let {
    onSelect,
    onCreate,
    placeholder = 'Buscar contato por nome, email ou telefone...',
    required = false,
    selectedContact = $bindable(null),
    class: className = ''
  } = $props();

  let searchTerm = $state('');
  let results = $state(/** @type {any[]} */ ([]));
  let isLoading = $state(false);
  let isOpen = $state(false);
  let showCreateModal = $state(false);
  /** @type {ReturnType<typeof setTimeout> | null} */
  let debounceTimer = $state(null);

  // Quick-create form state
  let newContact = $state({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    organization: ''
  });
  let isCreating = $state(false);

  /** @type {HTMLInputElement | null} */
  let inputRef = $state(null);

  /**
   * Search contacts via API with debounce
   * @param {string} query
   */
  async function searchContacts(query) {
    if (query.length < 2) {
      results = [];
      isOpen = false;
      return;
    }

    isLoading = true;
    try {
      const { apiRequest } = await import('$lib/api.js');
      const data = await apiRequest(`/contacts/search/?q=${encodeURIComponent(query)}`);
      results = data || [];
      isOpen = results.length > 0 || query.length >= 2;
    } catch (err) {
      console.error('Erro ao buscar contatos:', err);
      results = [];
    } finally {
      isLoading = false;
    }
  }

  /**
   * Handle input change with 300ms debounce
   */
  function handleInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      searchContacts(searchTerm);
    }, 300);
  }

  /**
   * Select a contact from results
   * @param {any} contact
   */
  function selectContact(contact) {
    selectedContact = contact;
    searchTerm = '';
    results = [];
    isOpen = false;
    onSelect?.(contact);
  }

  /** Clear selected contact */
  function clearSelection() {
    selectedContact = null;
    searchTerm = '';
    results = [];
  }

  /** Open quick-create modal */
  function openCreateModal() {
    // Pre-fill with search term
    const parts = searchTerm.trim().split(' ');
    newContact = {
      first_name: parts[0] || '',
      last_name: parts.slice(1).join(' ') || '',
      email: searchTerm.includes('@') ? searchTerm : '',
      phone: '',
      organization: ''
    };
    isOpen = false;
    showCreateModal = true;
  }

  /** Create new contact via API */
  async function handleCreateContact() {
    if (!newContact.first_name.trim()) {
      toast.error('Nome é obrigatório');
      return;
    }

    isCreating = true;
    try {
      const { apiRequest } = await import('$lib/api.js');
      const created = await apiRequest('/contacts/', {
        method: 'POST',
        body: newContact
      });

      // The API returns { error: false, message: "..." } on success
      // We need to search for the contact we just created to get full data
      if (created && !created.error) {
        // Search by the email or name to get the full contact object
        const searchResult = await apiRequest(
          `/contacts/search/?q=${encodeURIComponent(newContact.first_name)}`
        );
        const found = searchResult?.find(
          (/** @type {any} */ c) =>
            c.first_name === newContact.first_name && c.last_name === newContact.last_name
        );

        if (found) {
          selectContact(found);
        }

        toast.success('Contato criado com sucesso');
        showCreateModal = false;
        onCreate?.(found || created);
      } else {
        toast.error(created?.message || 'Erro ao criar contato');
      }
    } catch (err) {
      toast.error(`Erro ao criar contato: ${/** @type {Error} */ (err).message}`);
    } finally {
      isCreating = false;
    }
  }

  /** Handle blur — close dropdown after a short delay to allow click */
  function handleBlur() {
    setTimeout(() => {
      isOpen = false;
    }, 200);
  }
</script>

<div class="relative {className}">
  {#if selectedContact}
    <!-- Selected contact display -->
    <div
      class="flex items-center gap-3 rounded-md border border-input bg-background px-3 py-2 text-sm"
    >
      <div
        class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary"
      >
        {selectedContact.first_name?.[0]?.toUpperCase() || '?'}{selectedContact.last_name?.[0]?.toUpperCase() || ''}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate font-medium">
          {selectedContact.first_name} {selectedContact.last_name}
        </p>
        <div class="flex items-center gap-3 text-xs text-muted-foreground">
          {#if selectedContact.email}
            <span class="flex items-center gap-1 truncate">
              <Mail class="size-3" />{selectedContact.email}
            </span>
          {/if}
          {#if selectedContact.phone}
            <span class="flex items-center gap-1">
              <Phone class="size-3" />{selectedContact.phone}
            </span>
          {/if}
        </div>
      </div>
      <button
        type="button"
        onclick={clearSelection}
        class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        aria-label="Remover contato selecionado"
      >
        <X class="size-4" />
      </button>
    </div>
  {:else}
    <!-- Search input -->
    <div class="relative">
      <Search class="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
      <Input
        bind:ref={inputRef}
        bind:value={searchTerm}
        oninput={handleInput}
        onfocus={() => searchTerm.length >= 2 && (isOpen = true)}
        onblur={handleBlur}
        {placeholder}
        {required}
        class="pl-9 pr-9"
        autocomplete="off"
      />
      {#if isLoading}
        <Loader2 class="absolute right-2.5 top-2.5 size-4 animate-spin text-muted-foreground" />
      {/if}
    </div>

    <!-- Dropdown results -->
    {#if isOpen}
      <div
        class="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md"
        role="listbox"
        aria-label="Resultados da busca de contatos"
      >
        <div class="max-h-64 overflow-y-auto p-1">
          {#if results.length > 0}
            {#each results as contact (contact.id)}
              <button
                type="button"
                role="option"
                class="flex w-full items-center gap-3 rounded-sm px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                onmousedown={() => selectContact(contact)}
              >
                <div
                  class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary"
                >
                  {contact.first_name?.[0]?.toUpperCase() || '?'}{contact.last_name?.[0]?.toUpperCase() || ''}
                </div>
                <div class="min-w-0 flex-1">
                  <p class="truncate font-medium">
                    {contact.first_name} {contact.last_name}
                  </p>
                  <div class="flex items-center gap-3 text-xs text-muted-foreground">
                    {#if contact.email}
                      <span class="flex items-center gap-1 truncate">
                        <Mail class="size-3" />{contact.email}
                      </span>
                    {/if}
                    {#if contact.phone}
                      <span class="flex items-center gap-1">
                        <Phone class="size-3" />{contact.phone}
                      </span>
                    {/if}
                  </div>
                </div>
                {#if contact.account_name}
                  <span
                    class="flex shrink-0 items-center gap-1 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                  >
                    <Building2 class="size-3" />{contact.account_name}
                  </span>
                {/if}
              </button>
            {/each}
          {:else if searchTerm.length >= 2 && !isLoading}
            <p class="px-3 py-2 text-center text-sm text-muted-foreground">
              Nenhum contato encontrado
            </p>
          {/if}
        </div>

        <!-- Create new contact button -->
        <div class="border-t p-1">
          <button
            type="button"
            class="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm font-medium text-primary hover:bg-accent"
            onmousedown={openCreateModal}
          >
            <UserPlus class="size-4" />
            Criar novo contato
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- Quick-create contact modal -->
<Dialog.Root bind:open={showCreateModal}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Criar Novo Contato</Dialog.Title>
      <Dialog.Description>Preencha os dados básicos do contato.</Dialog.Description>
    </Dialog.Header>

    <div class="grid gap-4 py-4">
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-1.5">
          <Label for="new-first-name">Nome *</Label>
          <Input
            id="new-first-name"
            bind:value={newContact.first_name}
            placeholder="Nome"
            required
          />
        </div>
        <div class="space-y-1.5">
          <Label for="new-last-name">Sobrenome</Label>
          <Input id="new-last-name" bind:value={newContact.last_name} placeholder="Sobrenome" />
        </div>
      </div>
      <div class="space-y-1.5">
        <Label for="new-email">E-mail</Label>
        <Input id="new-email" type="email" bind:value={newContact.email} placeholder="email@exemplo.com" />
      </div>
      <div class="space-y-1.5">
        <Label for="new-phone">Telefone</Label>
        <Input id="new-phone" bind:value={newContact.phone} placeholder="(11) 99999-9999" />
      </div>
      <div class="space-y-1.5">
        <Label for="new-org">Empresa</Label>
        <Input id="new-org" bind:value={newContact.organization} placeholder="Nome da empresa" />
      </div>
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (showCreateModal = false)}>Cancelar</Button>
      <Button onclick={handleCreateContact} disabled={isCreating}>
        {#if isCreating}
          <Loader2 class="mr-2 size-4 animate-spin" />
        {/if}
        Criar Contato
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
