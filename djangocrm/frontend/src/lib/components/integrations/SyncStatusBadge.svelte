<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Loader2, CheckCircle2, XCircle, Clock } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {'pending' | 'in_progress' | 'completed' | 'failed'} status
   */

  /** @type {Props} */
  let { status = 'pending' } = $props();

  const config = $derived(/** @type {Record<string, {icon: any, label: string, variant: string}>} */ ({
    pending:     { icon: Clock,        label: 'Pendente',     variant: 'outline' },
    in_progress: { icon: Loader2,      label: 'Sincronizando', variant: 'secondary' },
    completed:   { icon: CheckCircle2, label: 'Concluído',    variant: 'default' },
    failed:      { icon: XCircle,      label: 'Falhou',       variant: 'destructive' },
  })[status] || { icon: Clock, label: status, variant: 'outline' });
</script>

<Badge variant={config.variant} class="gap-1 text-xs">
  {#if status === 'pending'}
    <Clock class="size-3" />
  {:else if status === 'in_progress'}
    <Loader2 class="size-3 animate-spin" />
  {:else if status === 'completed'}
    <CheckCircle2 class="size-3" />
  {:else if status === 'failed'}
    <XCircle class="size-3" />
  {:else}
    <Clock class="size-3" />
  {/if}
  {config.label}
</Badge>
