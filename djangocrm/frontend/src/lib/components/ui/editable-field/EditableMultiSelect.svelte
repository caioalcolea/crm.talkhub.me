<script>
  import { ChevronDown, X, Check, Search, Plus } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { cn } from '$lib/utils.js';

  /**
   * @typedef {Object} SelectOption
   * @property {string} id
   * @property {string} name
   * @property {string} [email]
   */

  /**
   * @type {{
   *   value?: string[],
   *   options?: SelectOption[],
   *   placeholder?: string,
   *   emptyText?: string,
   *   disabled?: boolean,
   *   onchange?: (value: string[]) => void,
   *   oncreate?: ((name: string) => Promise<any>) | null,
   *   class?: string,
   *   maxDisplay?: number,
   * }}
   */
  let {
    value = [],
    options = [],
    placeholder = 'Selecione...',
    emptyText = 'Nenhum selecionado',
    disabled = false,
    onchange,
    oncreate = null,
    class: className,
    maxDisplay = 3
  } = $props();

  let isOpen = $state(false);
  let searchQuery = $state('');

  /** @type {HTMLInputElement | null} */
  let searchInput = $state(null);

  /**
   * Toggle an option
   * @param {string} id
   */
  function toggleOption(id) {
    const newValue = value.includes(id) ? value.filter((v) => v !== id) : [...value, id];
    onchange?.(newValue);
  }

  /**
   * Remove an option
   * @param {Event} e
   * @param {string} id
   */
  function removeOption(e, id) {
    e.stopPropagation();
    e.preventDefault();
    const newValue = value.filter((v) => v !== id);
    onchange?.(newValue);
  }

  /**
   * Get selected options
   */
  const selectedOptions = $derived(options.filter((opt) => value.includes(opt.id)));

  /**
   * Get display options (limited to maxDisplay)
   */
  const displayOptions = $derived(selectedOptions.slice(0, maxDisplay));

  /**
   * Get remaining count
   */
  const remainingCount = $derived(
    selectedOptions.length > maxDisplay ? selectedOptions.length - maxDisplay : 0
  );

  /**
   * Filter options based on search query
   */
  const filteredOptions = $derived(
    searchQuery.trim()
      ? options.filter(
          (opt) =>
            opt.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (opt.email && opt.email.toLowerCase().includes(searchQuery.toLowerCase()))
        )
      : options
  );

  /**
   * Handle inline creation of a new option
   */
  async function handleCreate() {
    if (oncreate && searchQuery.trim()) {
      await oncreate(searchQuery.trim());
      searchQuery = '';
    }
  }

  /**
   * Focus search input when popover opens
   */
  $effect(() => {
    if (isOpen && searchInput) {
      // Small delay to let the popover render
      setTimeout(() => searchInput?.focus(), 50);
    }
    if (!isOpen) {
      searchQuery = '';
    }
  });
</script>

<div class={cn('group', className)}>
  <Popover.Root bind:open={isOpen}>
    <Popover.Trigger {disabled} class="w-full">
      <button
        type="button"
        class={cn(
          'flex min-h-[36px] w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
          !disabled && 'hover:bg-muted/50 cursor-pointer',
          disabled && 'cursor-default opacity-50'
        )}
      >
        <div class="flex flex-1 flex-wrap items-center gap-1.5">
          {#if selectedOptions.length === 0}
            <span class="text-muted-foreground italic">{emptyText}</span>
          {:else}
            {#each displayOptions as opt (opt.id)}
              <Badge variant="secondary" class="gap-1 pr-1">
                <span class="max-w-[120px] truncate">{opt.name}</span>
                {#if !disabled}
                  <button
                    type="button"
                    class="hover:bg-muted rounded-sm p-0.5"
                    onclick={(e) => removeOption(e, opt.id)}
                  >
                    <X class="h-3 w-3" />
                  </button>
                {/if}
              </Badge>
            {/each}
            {#if remainingCount > 0}
              <Badge variant="outline" class="text-xs">+{remainingCount}</Badge>
            {/if}
          {/if}
        </div>
        <ChevronDown
          class={cn(
            'text-muted-foreground h-4 w-4 shrink-0 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>
    </Popover.Trigger>
    <Popover.Content class="w-64 p-0" align="start" sideOffset={4}>
      <!-- Search input -->
      <div class="border-border/40 flex items-center gap-2 border-b px-3 py-2">
        <Search class="text-muted-foreground h-4 w-4 shrink-0" />
        <input
          bind:this={searchInput}
          type="text"
          placeholder="Buscar..."
          bind:value={searchQuery}
          class="placeholder:text-muted-foreground/50 h-8 w-full bg-transparent text-sm outline-none"
        />
      </div>
      <!-- Options list -->
      <div class="max-h-56 overflow-y-auto p-1">
        {#if filteredOptions.length === 0 && !(searchQuery.trim() && oncreate)}
          <div class="text-muted-foreground px-2 py-4 text-center text-sm">
            {searchQuery ? 'Nenhum resultado' : 'Nenhuma opção disponível'}
          </div>
        {:else if filteredOptions.length > 0}
          {#each filteredOptions as opt (opt.id)}
            {@const isSelected = value.includes(opt.id)}
            <button
              type="button"
              onclick={() => toggleOption(opt.id)}
              class={cn(
                'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors',
                'hover:bg-accent hover:text-accent-foreground cursor-pointer',
                isSelected && 'bg-accent/50'
              )}
            >
              <div
                class={cn(
                  'flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border transition-colors',
                  isSelected
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-muted-foreground/30'
                )}
              >
                {#if isSelected}
                  <Check class="h-3 w-3" />
                {/if}
              </div>
              <div class="min-w-0 flex-1 text-left">
                <span class="truncate">{opt.name}</span>
                {#if opt.email}
                  <span class="text-muted-foreground block truncate text-xs">{opt.email}</span>
                {/if}
              </div>
            </button>
          {/each}
        {/if}
        {#if searchQuery.trim() && oncreate}
          <button
            type="button"
            onclick={handleCreate}
            class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground cursor-pointer text-primary"
          >
            <Plus class="h-4 w-4" />
            <span>Criar "<strong>{searchQuery.trim()}</strong>"</span>
          </button>
        {/if}
      </div>
      <!-- Selection count footer -->
      {#if selectedOptions.length > 0}
        <div class="border-border/40 border-t px-3 py-1.5">
          <span class="text-muted-foreground text-xs">{selectedOptions.length} selecionado{selectedOptions.length > 1 ? 's' : ''}</span>
        </div>
      {/if}
    </Popover.Content>
  </Popover.Root>
</div>
