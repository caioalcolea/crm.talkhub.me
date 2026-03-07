<script>
  import * as Tooltip from '$lib/components/ui/tooltip/index.js';

  /**
   * @typedef {Object} Props
   * @property {'healthy' | 'degraded' | 'down' | 'unknown'} status
   */

  /** @type {Props} */
  let { status = 'unknown' } = $props();

  const config = $derived(/** @type {Record<string, {color: string, bg: string, label: string}>} */ ({
    healthy:  { color: 'bg-emerald-500', bg: 'bg-emerald-100 dark:bg-emerald-950', label: 'Saudável' },
    degraded: { color: 'bg-amber-500',   bg: 'bg-amber-100 dark:bg-amber-950',     label: 'Degradado' },
    down:     { color: 'bg-red-500',      bg: 'bg-red-100 dark:bg-red-950',         label: 'Indisponível' },
    unknown:  { color: 'bg-gray-400',     bg: 'bg-gray-100 dark:bg-gray-900',       label: 'Desconhecido' },
  })[status] || { color: 'bg-gray-400', bg: 'bg-gray-100 dark:bg-gray-900', label: 'Desconhecido' });
</script>

<Tooltip.Root>
  <Tooltip.Trigger>
    <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium {config.bg}">
      <span class="size-2 rounded-full {config.color}"></span>
      {config.label}
    </span>
  </Tooltip.Trigger>
  <Tooltip.Content>
    <p>Status: {config.label}</p>
  </Tooltip.Content>
</Tooltip.Root>
