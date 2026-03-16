<script>
  import { Building2, DollarSign, Percent, Clock, AlertCircle } from '@lucide/svelte';

  /**
   * @typedef {Object} Opportunity
   * @property {string} id
   * @property {string} name
   * @property {string} [account_name]
   * @property {number|string} [amount]
   * @property {string} [currency]
   * @property {number} [probability]
   * @property {string} [stage]
   * @property {string} [closed_on]
   * @property {string} [aging_status]
   * @property {number} [days_in_stage]
   * @property {Array<{id: string, user_details?: {email?: string}, email?: string}>} [assigned_to]
   */

  /** @type {{ item: Opportunity, onclick?: () => void, ondragstart?: (e: DragEvent) => void, ondragend?: () => void }} */
  let { item, onclick, ondragstart, ondragend } = $props();

  const accountName = $derived(item.account_name || '');
  const amount = $derived(item.amount);
  const currency = $derived(item.currency || 'BRL');
  const probability = $derived(item.probability ?? 0);
  const agingStatus = $derived(item.aging_status || 'green');
  const daysInStage = $derived(item.days_in_stage ?? 0);
  const assignees = $derived(item.assigned_to || []);

  /**
   * Format currency amount with compact notation
   * @param {number|string} value
   * @param {string} curr
   */
  function formatAmount(value, curr) {
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '';
    try {
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: curr,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
        notation: num >= 100000 ? 'compact' : 'standard'
      }).format(num);
    } catch {
      return `${curr} ${num.toLocaleString('pt-BR')}`;
    }
  }

  const agingColors = {
    green: 'bg-emerald-500',
    yellow: 'bg-amber-500',
    red: 'bg-rose-500'
  };

  function getAssigneeInitials(assignee) {
    const email = assignee?.user_details?.email || assignee?.email || '';
    if (!email) return '?';
    return email.charAt(0).toUpperCase();
  }

  function getAssigneeName(assignee) {
    return assignee?.user_details?.email || assignee?.email || 'Desconhecido';
  }

  function getAvatarColor(email) {
    const colors = [
      'from-violet-500 to-purple-600',
      'from-cyan-500 to-blue-600',
      'from-emerald-500 to-teal-600',
      'from-amber-500 to-orange-600',
      'from-rose-500 to-pink-600',
      'from-indigo-500 to-blue-600'
    ];
    const hash = (email || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onclick?.();
    }
  }
</script>

<div
  class="opp-card group relative cursor-pointer overflow-hidden rounded-xl border border-white/10 bg-white/80 backdrop-blur-sm transition-all duration-300 ease-out
    hover:-translate-y-0.5 hover:border-white/20 hover:shadow-lg hover:shadow-black/5
    dark:border-white/[0.06] dark:bg-white/[0.03] dark:hover:border-white/[0.1] dark:hover:shadow-black/20
    {agingStatus === 'red' ? 'border-l-[3px] border-l-rose-500' : ''}"
  draggable="true"
  {onclick}
  onkeydown={handleKeydown}
  {ondragstart}
  {ondragend}
  role="button"
  tabindex="0"
>
  <div class="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/50 via-transparent to-transparent dark:from-white/[0.02]"></div>

  <div class="relative p-3.5">
    <!-- Header: Name + Aging indicator -->
    <div class="flex items-start justify-between gap-2">
      <h4 class="flex-1 truncate text-[0.9rem] leading-tight font-semibold tracking-tight text-gray-900 dark:text-white/95">
        {item.name}
      </h4>

      {#if daysInStage > 0}
        <div
          class="flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[0.6rem] font-medium
            {agingStatus === 'red'
              ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
              : agingStatus === 'yellow'
                ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                : 'bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400'}"
          title="{daysInStage} dias neste estágio"
        >
          <div class="h-1.5 w-1.5 rounded-full {agingColors[agingStatus] || 'bg-gray-400'}"></div>
          {daysInStage}d
        </div>
      {/if}
    </div>

    <!-- Account -->
    {#if accountName}
      <div class="mt-1.5 flex items-center gap-1.5">
        <Building2 class="h-3.5 w-3.5 shrink-0 text-gray-400 dark:text-gray-500" />
        <span class="truncate text-sm text-gray-600 dark:text-gray-400">{accountName}</span>
      </div>
    {/if}

    <!-- Amount + Probability -->
    <div class="mt-3 flex items-center gap-2">
      {#if amount}
        <div class="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-emerald-500/10 to-teal-500/10 px-2.5 py-1.5 dark:from-emerald-500/15 dark:to-teal-500/15">
          <DollarSign class="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          <span class="text-sm font-bold tracking-tight text-emerald-700 dark:text-emerald-300">
            {formatAmount(amount, currency)}
          </span>
        </div>
      {/if}

      {#if probability > 0}
        <div class="flex items-center gap-1 rounded-lg bg-blue-500/10 px-2 py-1.5 dark:bg-blue-500/15">
          <Percent class="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          <span class="text-xs font-bold text-blue-700 dark:text-blue-300">{probability}%</span>
        </div>
      {/if}
    </div>

    <!-- Footer: Assignees -->
    {#if assignees.length > 0}
      <div class="mt-3 flex items-center justify-between">
        <div class="flex items-center -space-x-2">
          {#each assignees.slice(0, 3) as assignee, i (assignee.id)}
            <div
              class="relative flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br {getAvatarColor(getAssigneeName(assignee))} text-[0.7rem] font-semibold text-white shadow-sm ring-2 ring-white dark:ring-gray-900"
              style="z-index: {3 - i}"
              title={getAssigneeName(assignee)}
            >
              {getAssigneeInitials(assignee)}
            </div>
          {/each}
          {#if assignees.length > 3}
            <div
              class="relative flex h-7 w-7 items-center justify-center rounded-full bg-gray-200 text-[0.65rem] font-bold text-gray-600 ring-2 ring-white dark:bg-gray-700 dark:text-gray-300 dark:ring-gray-900"
              style="z-index: 0"
            >
              +{assignees.length - 3}
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .opp-card {
    --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06);
    box-shadow: var(--card-shadow);
  }

  .opp-card:hover {
    --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
  }

  :global(.dark) .opp-card {
    --card-shadow:
      0 1px 3px rgba(0, 0, 0, 0.2), 0 1px 2px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  :global(.dark) .opp-card:hover {
    --card-shadow:
      0 20px 40px -10px rgba(0, 0, 0, 0.4), 0 8px 20px -8px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }

  .opp-card:active {
    cursor: grabbing;
    transform: rotate(1.5deg) scale(1.03);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.2);
  }

  :global(.dark) .opp-card:active {
    box-shadow:
      0 25px 50px -12px rgba(0, 0, 0, 0.5),
      0 0 30px -5px rgba(34, 211, 238, 0.15);
  }

  .opp-card:focus-visible {
    outline: 2px solid rgb(34 211 238);
    outline-offset: 2px;
  }
</style>
