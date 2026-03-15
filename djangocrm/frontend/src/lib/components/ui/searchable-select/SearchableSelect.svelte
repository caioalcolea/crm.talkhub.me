<script>
  import { ChevronsUpDown, Check, Search, X } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import { cn } from '$lib/utils.js';
  import { tick } from 'svelte';

  /**
   * @type {{
   *   value?: string,
   *   options?: { value: string, label: string }[],
   *   groups?: { label: string, options: { value: string, label: string }[] }[],
   *   placeholder?: string,
   *   searchPlaceholder?: string,
   *   emptyText?: string,
   *   allowClear?: boolean,
   *   disabled?: boolean,
   *   class?: string,
   *   onchange?: (value: string) => void
   * }}
   */
  let {
    value = $bindable(''),
    options = [],
    groups = [],
    placeholder = 'Selecione...',
    searchPlaceholder = 'Buscar...',
    emptyText = 'Nenhum item encontrado.',
    allowClear = true,
    disabled = false,
    class: className = '',
    onchange
  } = $props();

  let open = $state(false);
  let search = $state('');
  /** @type {HTMLInputElement|null} */
  let searchInput = $state(null);

  // Build a unified flat list for lookup
  let allOptions = $derived.by(() => {
    if (groups.length > 0) {
      return groups.flatMap((g) => g.options);
    }
    return options;
  });

  let selectedLabel = $derived(
    allOptions.find((o) => o.value === value)?.label || ''
  );

  let searchLower = $derived(search.toLowerCase());

  // Filter grouped items
  let filteredGroups = $derived.by(() => {
    if (groups.length === 0) return [];
    if (!searchLower) return groups;
    return groups
      .map((g) => ({
        label: g.label,
        options: g.options.filter((o) => o.label.toLowerCase().includes(searchLower))
      }))
      .filter((g) => g.options.length > 0);
  });

  // Filter flat items
  let filteredOptions = $derived.by(() => {
    if (groups.length > 0) return [];
    if (!searchLower) return options;
    return options.filter((o) => o.label.toLowerCase().includes(searchLower));
  });

  function select(val) {
    value = val;
    open = false;
    search = '';
    onchange?.(val);
  }

  function clear(e) {
    e.stopPropagation();
    value = '';
    onchange?.('');
  }

  // Focus search input when popover opens
  $effect(() => {
    if (open) {
      tick().then(() => searchInput?.focus());
    } else {
      search = '';
    }
  });
</script>

<Popover.Root bind:open>
  <Popover.Trigger
    class={cn(
      'border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-9 w-full items-center justify-between rounded-md border px-3 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
      className
    )}
    {disabled}
    role="combobox"
    aria-expanded={open}
  >
    <span class="truncate {!selectedLabel ? 'text-muted-foreground' : ''}">
      {selectedLabel || placeholder}
    </span>
    <div class="ml-1 flex shrink-0 items-center gap-0.5">
      {#if allowClear && value}
        <button
          type="button"
          class="text-muted-foreground hover:text-foreground rounded p-0.5 transition-colors"
          onclick={clear}
          tabindex={-1}
        >
          <X class="size-3.5" />
        </button>
      {/if}
      <ChevronsUpDown class="text-muted-foreground size-3.5 shrink-0" />
    </div>
  </Popover.Trigger>

  <Popover.Content class="w-(--bits-popover-anchor-width) p-0" align="start" sideOffset={4}>
    <!-- Search input -->
    <div class="border-b px-3 py-2">
      <div class="relative">
        <Search class="text-muted-foreground absolute left-0 top-1/2 size-3.5 -translate-y-1/2" />
        <input
          bind:this={searchInput}
          bind:value={search}
          placeholder={searchPlaceholder}
          class="bg-transparent placeholder:text-muted-foreground w-full pl-5 text-sm outline-none"
        />
      </div>
    </div>

    <!-- Options list -->
    <div class="max-h-[240px] overflow-y-auto p-1">
      {#if groups.length > 0}
        <!-- Grouped mode -->
        {#if filteredGroups.length === 0}
          <div class="text-muted-foreground py-4 text-center text-sm">{emptyText}</div>
        {:else}
          {#each filteredGroups as group (group.label)}
            <div class="px-2 pt-2 pb-1">
              <span class="text-muted-foreground text-[11px] font-semibold uppercase tracking-wider">
                {group.label}
              </span>
            </div>
            {#each group.options as opt (opt.value)}
              <button
                type="button"
                class="hover:bg-accent hover:text-accent-foreground flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors"
                onclick={() => select(opt.value)}
              >
                <Check class="size-3.5 shrink-0 {opt.value === value ? 'opacity-100' : 'opacity-0'}" />
                <span class="truncate">{opt.label}</span>
              </button>
            {/each}
          {/each}
        {/if}
      {:else}
        <!-- Flat mode -->
        {#if filteredOptions.length === 0}
          <div class="text-muted-foreground py-4 text-center text-sm">{emptyText}</div>
        {:else}
          {#each filteredOptions as opt (opt.value)}
            <button
              type="button"
              class="hover:bg-accent hover:text-accent-foreground flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors"
              onclick={() => select(opt.value)}
            >
              <Check class="size-3.5 shrink-0 {opt.value === value ? 'opacity-100' : 'opacity-0'}" />
              <span class="truncate">{opt.label}</span>
            </button>
          {/each}
        {/if}
      {/if}
    </div>
  </Popover.Content>
</Popover.Root>
