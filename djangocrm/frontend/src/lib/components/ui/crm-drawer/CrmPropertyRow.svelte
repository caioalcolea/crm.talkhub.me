<script>
  import { Check, Calendar as CalendarIcon, Plus, Search } from '@lucide/svelte';
  import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import { Calendar } from '$lib/components/ui/calendar/index.js';
  import { EditableMultiSelect } from '$lib/components/ui/editable-field/index.js';
  import { cn } from '$lib/utils.js';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { parseDate, getLocalTimeZone } from '@internationalized/date';

  /**
   * @type {{
   *   label: string,
   *   value?: any,
   *   type?: 'text' | 'email' | 'number' | 'date' | 'time' | 'select' | 'checkbox' | 'boolean' | 'multiselect' | 'textarea' | 'color' | 'combobox',
   *   icon?: import('svelte').Component,
   *   options?: any[],
   *   placeholder?: string,
   *   emptyText?: string,
   *   editable?: boolean,
   *   prefix?: string,
   *   onchange?: (value: any) => void,
   *   oncreate?: (name: string) => void,
   *   class?: string,
   * }}
   */
  let {
    label,
    value = '',
    type = 'text',
    icon: Icon,
    options = [],
    placeholder = '',
    emptyText = '',
    editable = true,
    prefix = '',
    onchange,
    oncreate,
    class: className
  } = $props();

  /**
   * Get option style for select
   * @param {string} val
   */
  function getOptionStyle(val) {
    if (type !== 'select') return '';
    const opt = options.find((/** @type {any} */ o) => o.value === val);
    return opt?.color || 'bg-gray-100 text-gray-700';
  }

  /**
   * Get option label for select
   * @param {string} val
   */
  function getOptionLabel(val) {
    if (type !== 'select') return val;
    const opt = options.find((/** @type {any} */ o) => o.value === val);
    return opt?.label || val || emptyText || 'Selecione...';
  }

  /**
   * Get option background color class (for the dot)
   * @param {string} val
   */
  function getOptionBgColor(val) {
    if (type !== 'select') return '';
    const opt = options.find((/** @type {any} */ o) => o.value === val);
    if (!opt?.color) return 'bg-gray-400';
    // Extract bg class from color string (e.g., "bg-emerald-100 text-emerald-700" -> "bg-emerald-500")
    const match = opt.color.match(/bg-(\w+)-\d+/);
    if (match) {
      return `bg-${match[1]}-500`;
    }
    return 'bg-gray-400';
  }

  /**
   * Parse string date to DateValue
   * @param {string} dateStr
   */
  function parseDateValue(dateStr) {
    if (!dateStr) return undefined;
    try {
      // parseDate expects YYYY-MM-DD; strip time portion from datetime strings
      const dateOnly = dateStr.includes('T') ? dateStr.split('T')[0] : dateStr;
      return parseDate(dateOnly);
    } catch {
      return undefined;
    }
  }

  /**
   * Format date for display
   * @param {string} dateStr
   */
  function formatDateDisplay(dateStr) {
    if (!dateStr) return placeholder || 'Escolha uma data';
    try {
      // Handle both date-only (YYYY-MM-DD) and full datetime (ISO 8601) strings
      const date = dateStr.includes('T')
        ? new Date(dateStr)
        : new Date(dateStr + 'T00:00:00');
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString('pt-BR', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  }

  /**
   * Handle calendar date change
   * @param {import('@internationalized/date').DateValue | undefined} dateValue
   */
  function handleCalendarChange(dateValue) {
    if (dateValue) {
      onchange?.(dateValue.toString());
      datePopoverOpen = false;
    }
  }

  // State for date popover
  let datePopoverOpen = $state(false);

  /**
   * Format number with optional currency
   * @param {number | string} val
   */
  function formatNumber(val) {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    if (isNaN(num)) return emptyText || '0';
    if (prefix === '$') {
      return formatCurrency(num);
    }
    return prefix + num.toLocaleString();
  }

  /**
   * Handle text input
   * @param {Event} e
   */
  function handleInput(e) {
    const target = /** @type {HTMLInputElement} */ (e.target);
    onchange?.(target.value);
  }

  /**
   * Handle number input
   * @param {Event} e
   */
  function handleNumberInput(e) {
    const target = /** @type {HTMLInputElement} */ (e.target);
    onchange?.(parseFloat(target.value) || 0);
  }

  /**
   * Handle checkbox toggle
   */
  function handleCheckboxToggle() {
    onchange?.(!value);
  }

  /**
   * Handle color input
   * @param {Event} e
   */
  function handleColorInput(e) {
    const target = /** @type {HTMLInputElement} */ (e.target);
    onchange?.(target.value);
  }

  /**
   * Handle select change
   * @param {string} newValue
   */
  function handleSelectChange(newValue) {
    onchange?.(newValue);
  }

  /**
   * Handle multiselect change
   * @param {string[]} newValue
   */
  function handleMultiSelectChange(newValue) {
    onchange?.(newValue);
  }

  // Combobox state
  let comboboxOpen = $state(false);
  let comboboxSearch = $state('');

  /**
   * Get filtered options for combobox
   */
  const comboboxFiltered = $derived(
    comboboxSearch
      ? options.filter((o) => o.name?.toLowerCase().includes(comboboxSearch.toLowerCase()))
      : options
  );

  /**
   * Get display label for combobox value
   */
  const comboboxDisplayLabel = $derived(() => {
    if (!value) return '';
    const opt = options.find((o) => o.id === value);
    return opt?.name || '';
  });

  /**
   * Handle combobox selection
   * @param {any} option
   */
  function handleComboboxSelect(option) {
    onchange?.(option.id);
    comboboxOpen = false;
    comboboxSearch = '';
  }

  /**
   * Handle combobox clear
   */
  function handleComboboxClear() {
    onchange?.(null);
    comboboxOpen = false;
    comboboxSearch = '';
  }

  /**
   * Handle combobox create new
   */
  function handleComboboxCreate() {
    if (comboboxSearch && oncreate) {
      oncreate(comboboxSearch);
      comboboxOpen = false;
      comboboxSearch = '';
    }
  }
</script>

<div
  class={cn(
    'group hover:bg-muted/40 -mx-3 flex min-h-[44px] items-center rounded-lg px-3 transition-all duration-150',
    className
  )}
>
  <!-- Label with icon -->
  <div
    class="text-muted-foreground flex w-32 shrink-0 items-center gap-2.5 text-[13px] font-medium"
  >
    {#if Icon}
      <div class="bg-muted/50 flex h-6 w-6 items-center justify-center rounded-md">
        <Icon class="text-muted-foreground/70 h-3.5 w-3.5" />
      </div>
    {/if}
    {label}
  </div>

  <!-- Value -->
  <div class="min-w-0 flex-1">
    {#if type === 'text' || type === 'email'}
      <input
        {type}
        {value}
        oninput={handleInput}
        {placeholder}
        disabled={!editable}
        class="text-foreground placeholder:text-muted-foreground/40 focus:bg-muted/30 focus:ring-primary/20 w-full rounded-lg border-0 bg-transparent px-2.5 py-1.5 text-sm font-medium transition-all outline-none focus:ring-1"
      />
    {:else if type === 'number'}
      <div class="flex items-center">
        {#if prefix}
          <span class="text-muted-foreground mr-1.5 text-sm font-medium">{prefix}</span>
        {/if}
        <input
          type="number"
          value={value || 0}
          oninput={handleNumberInput}
          {placeholder}
          disabled={!editable}
          class="text-foreground placeholder:text-muted-foreground/40 focus:bg-muted/30 focus:ring-primary/20 w-full rounded-lg border-0 bg-transparent px-2 py-1.5 text-sm font-medium tabular-nums transition-all outline-none focus:ring-1"
        />
      </div>
    {:else if type === 'date'}
      <Popover.Root bind:open={datePopoverOpen}>
        <Popover.Trigger disabled={!editable} class="w-full">
          {#snippet child({ props })}
            <button
              {...props}
              type="button"
              class={cn(
                'hover:bg-muted/30 inline-flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-all',
                !value ? 'text-muted-foreground/50' : 'text-foreground'
              )}
            >
              <CalendarIcon class="text-muted-foreground/60 h-3.5 w-3.5 shrink-0" />
              {formatDateDisplay(value)}
            </button>
          {/snippet}
        </Popover.Trigger>
        <Popover.Content class="w-auto p-0" align="start">
          <Calendar value={parseDateValue(value)} onValueChange={handleCalendarChange} />
        </Popover.Content>
      </Popover.Root>
    {:else if type === 'time'}
      <div class="flex items-center gap-2 px-2.5 py-1">
        {#if icon}
          <svelte:component this={icon} class="text-muted-foreground/60 h-3.5 w-3.5 shrink-0" />
        {/if}
        <input
          type="time"
          value={value || ''}
          oninput={(e) => onchange?.(e.target.value)}
          disabled={!editable}
          class={cn(
            'text-foreground bg-transparent border-0 text-sm font-medium outline-none',
            !value && 'text-muted-foreground/50'
          )}
        />
      </div>
    {:else if type === 'textarea'}
      <textarea
        oninput={handleInput}
        {placeholder}
        disabled={!editable}
        rows={3}
        class="text-foreground placeholder:text-muted-foreground/40 focus:bg-muted/30 focus:ring-primary/20 w-full resize-none rounded-lg border-0 bg-transparent px-2.5 py-1.5 text-sm transition-all outline-none focus:ring-1"
        >{value || ''}</textarea
      >
    {:else if type === 'select'}
      <DropdownMenu.Root>
        <DropdownMenu.Trigger disabled={!editable}>
          {#snippet child({ props })}
            <button
              {...props}
              type="button"
              class="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold shadow-sm ring-1 ring-black/5 transition-all duration-150 ring-inset hover:shadow dark:ring-white/10 {getOptionStyle(
                value
              )}"
            >
              <span
                class="h-2 w-2 rounded-full ring-1 ring-black/10 ring-inset dark:ring-white/20 {getOptionBgColor(
                  value
                )}"
              ></span>
              {getOptionLabel(value)}
            </button>
          {/snippet}
        </DropdownMenu.Trigger>
        <DropdownMenu.Content align="start" class="min-w-48 p-1.5">
          {#each options as option (option.value)}
            <DropdownMenu.Item
              onclick={() => handleSelectChange(option.value)}
              class="flex items-center gap-2.5 rounded-lg px-2.5 py-2"
            >
              <span
                class="h-2.5 w-2.5 rounded-full ring-1 ring-black/10 ring-inset dark:ring-white/20 {option.color?.split(
                  ' '
                )[0] || 'bg-gray-400'}"
              ></span>
              <span class="font-medium">{option.label}</span>
              {#if value === option.value}
                <Check class="text-primary ml-auto h-4 w-4" />
              {/if}
            </DropdownMenu.Item>
          {/each}
        </DropdownMenu.Content>
      </DropdownMenu.Root>
    {:else if type === 'checkbox' || type === 'boolean'}
      <button
        type="button"
        onclick={handleCheckboxToggle}
        disabled={!editable}
        class="flex h-5 w-5 items-center justify-center rounded-md border-2 transition-all duration-150 {value
          ? 'border-primary bg-primary shadow-primary/25 shadow-sm'
          : 'border-muted-foreground/30 hover:border-muted-foreground/50'}"
      >
        {#if value}
          <Check class="text-primary-foreground h-3.5 w-3.5" />
        {/if}
      </button>
    {:else if type === 'color'}
      <div class="flex items-center gap-3 px-2 py-1">
        <input
          type="color"
          value={value || '#3B82F6'}
          oninput={handleColorInput}
          disabled={!editable}
          class="border-border/50 h-8 w-10 cursor-pointer rounded-lg border bg-transparent p-0.5 shadow-sm"
        />
        <span class="text-muted-foreground font-mono text-xs">{value || '#3B82F6'}</span>
      </div>
    {:else if type === 'multiselect'}
      <EditableMultiSelect
        value={Array.isArray(value) ? value : []}
        {options}
        {placeholder}
        emptyText={emptyText || 'Nenhum selecionado'}
        disabled={!editable}
        onchange={handleMultiSelectChange}
      />
    {:else if type === 'combobox'}
      <Popover.Root bind:open={comboboxOpen}>
        <Popover.Trigger disabled={!editable} class="w-full">
          {#snippet child({ props })}
            <button
              {...props}
              type="button"
              class={cn(
                'hover:bg-muted/30 inline-flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-all text-left',
                !value ? 'text-muted-foreground/50' : 'text-foreground'
              )}
            >
              {comboboxDisplayLabel() || (value ? String(value) : '') || placeholder || 'Selecionar...'}
            </button>
          {/snippet}
        </Popover.Trigger>
        <Popover.Content class="w-64 p-0" align="start">
          <div class="flex items-center border-b px-3 py-2">
            <Search class="text-muted-foreground mr-2 h-4 w-4 shrink-0" />
            <input
              type="text"
              bind:value={comboboxSearch}
              placeholder="Buscar..."
              class="placeholder:text-muted-foreground flex h-8 w-full bg-transparent text-sm outline-none"
            />
          </div>
          <div class="max-h-48 overflow-y-auto p-1">
            {#if value}
              <button
                type="button"
                onclick={handleComboboxClear}
                class="text-muted-foreground hover:bg-muted/50 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm italic"
              >
                Remover seleção
              </button>
            {/if}
            {#each comboboxFiltered as option (option.id)}
              <button
                type="button"
                onclick={() => handleComboboxSelect(option)}
                class="hover:bg-muted/50 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm"
              >
                <span class="flex-1 truncate text-left">{option.name}</span>
                {#if value === option.id}
                  <Check class="text-primary h-4 w-4 shrink-0" />
                {/if}
              </button>
            {/each}
            {#if comboboxFiltered.length === 0 && !comboboxSearch}
              <p class="text-muted-foreground px-2 py-3 text-center text-sm">
                {emptyText || 'Nenhuma opção'}
              </p>
            {/if}
            {#if comboboxSearch && oncreate}
              <button
                type="button"
                onclick={handleComboboxCreate}
                class="text-primary hover:bg-primary/10 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium"
              >
                <Plus class="h-4 w-4" />
                Criar "{comboboxSearch}"
              </button>
            {/if}
          </div>
        </Popover.Content>
      </Popover.Root>
    {:else if type === 'readonly'}
      <span class="text-foreground px-2.5 py-1.5 text-sm font-medium">
        {#if value}
          {value}
        {:else}
          <span class="text-muted-foreground/40 italic">{emptyText || '—'}</span>
        {/if}
      </span>
    {/if}
  </div>
</div>
