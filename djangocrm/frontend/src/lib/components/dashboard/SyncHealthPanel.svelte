<script>
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import IntegrationHealth from '$lib/components/integrations/IntegrationHealth.svelte';
  import { Activity, RefreshCw } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} integrations
   */

  /** @type {Props} */
  let { integrations = [] } = $props();

  /** @param {string} dateStr */
  function timeAgo(dateStr) {
    if (!dateStr) return 'Nunca';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Agora';
    if (mins < 60) return `${mins}min atrás`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h atrás`;
    return `${Math.floor(hours / 24)}d atrás`;
  }
</script>

<Card.Root>
  <Card.Header class="pb-3">
    <Card.Title class="flex items-center gap-2 text-sm">
      <Activity class="size-4" />
      Saúde das Integrações
    </Card.Title>
  </Card.Header>
  <Card.Content>
    {#if integrations.length === 0}
      <p class="text-xs text-muted-foreground py-4 text-center">Nenhuma integração configurada</p>
    {:else}
      <div class="divide-y">
        {#each integrations as integration (integration.slug)}
          <div class="flex items-center gap-3 py-2">
            <IntegrationHealth status={integration.health_status || 'unknown'} />
            <div class="flex-1 min-w-0">
              <p class="text-sm truncate">{integration.name || integration.slug}</p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <Badge variant={integration.is_active ? 'default' : 'secondary'} class="text-[10px]">
                {integration.is_active ? 'Ativo' : 'Inativo'}
              </Badge>
              {#if integration.last_sync_at}
                <span class="text-[10px] text-muted-foreground flex items-center gap-1">
                  <RefreshCw class="size-2.5" />
                  {timeAgo(integration.last_sync_at)}
                </span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </Card.Content>
</Card.Root>
