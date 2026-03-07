<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Tooltip from '$lib/components/ui/tooltip/index.js';
  import { Clock, AlertTriangle, CheckCircle } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} [slaDeadline] - ISO datetime of SLA deadline
   * @property {boolean} [slaBreached] - Whether SLA has been breached
   * @property {number} [slaHours] - Configured SLA hours
   * @property {string} [createdAt] - Case creation time
   */

  /** @type {Props} */
  let { slaDeadline = '', slaBreached = false, slaHours = 0, createdAt = '' } = $props();

  let status = $derived(computeStatus());
  let timeRemaining = $derived(computeTimeRemaining());

  function computeStatus() {
    if (slaBreached) return 'breached';
    if (!slaDeadline) return 'none';
    const now = Date.now();
    const deadline = new Date(slaDeadline).getTime();
    const total = slaHours * 3600000;
    const remaining = deadline - now;
    if (remaining <= 0) return 'breached';
    if (remaining < total * 0.25) return 'warning';
    return 'ok';
  }

  function computeTimeRemaining() {
    if (!slaDeadline) return '';
    const remaining = new Date(slaDeadline).getTime() - Date.now();
    if (remaining <= 0) return 'SLA expirado';
    const hours = Math.floor(remaining / 3600000);
    const mins = Math.floor((remaining % 3600000) / 60000);
    if (hours > 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
    return `${hours}h ${mins}min`;
  }

  const statusConfig = {
    ok: { color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', icon: CheckCircle, label: 'Dentro do prazo' },
    warning: { color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', icon: Clock, label: 'Atenção' },
    breached: { color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: AlertTriangle, label: 'SLA violado' },
    none: { color: '', icon: null, label: '' }
  };

  let config = $derived(statusConfig[status] || statusConfig.none);
</script>

{#if status !== 'none'}
  <Tooltip.Root>
    <Tooltip.Trigger>
      <Badge variant="outline" class="gap-1 px-1.5 py-0 text-[10px] {config.color}">
        {#if status === 'ok'}
          <CheckCircle class="size-3" />
        {:else if status === 'warning'}
          <Clock class="size-3" />
        {:else if status === 'breached'}
          <AlertTriangle class="size-3" />
        {/if}
        {status === 'breached' ? 'SLA' : timeRemaining}
      </Badge>
    </Tooltip.Trigger>
    <Tooltip.Content>
      <p class="text-xs">{config.label}</p>
      {#if slaHours}
        <p class="text-xs text-muted-foreground">SLA: {slaHours}h</p>
      {/if}
      {#if timeRemaining}
        <p class="text-xs text-muted-foreground">{timeRemaining}</p>
      {/if}
    </Tooltip.Content>
  </Tooltip.Root>
{/if}
