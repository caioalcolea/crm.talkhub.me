<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Workflow } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} flows
   */

  /** @type {Props} */
  let { flows = [] } = $props();
</script>

<div class="space-y-2">
  {#each flows as flow (flow.id || flow.name)}
    <div class="flex items-center gap-3 rounded-lg bg-muted/50 px-3 py-2">
      <Workflow class="size-4 text-muted-foreground shrink-0" />
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium truncate">{flow.name}</p>
        {#if flow.channel}
          <p class="text-muted-foreground text-xs">{flow.channel}</p>
        {/if}
      </div>
      <Badge variant={flow.active ? 'default' : 'secondary'} class="text-xs">
        {flow.active ? 'Ativo' : 'Inativo'}
      </Badge>
    </div>
  {:else}
    <p class="text-muted-foreground text-sm text-center py-4">Nenhum fluxo encontrado.</p>
  {/each}
</div>
