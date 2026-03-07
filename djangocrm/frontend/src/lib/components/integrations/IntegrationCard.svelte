<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Settings, RefreshCw, Plug } from '@lucide/svelte';
  import IntegrationHealth from './IntegrationHealth.svelte';
  import SyncStatusBadge from './SyncStatusBadge.svelte';

  /**
   * @typedef {Object} Props
   * @property {any} integration
   */

  /** @type {Props} */
  let { integration } = $props();

  let slug = $derived(integration.slug || integration.connector_slug || '');
  let lastSync = $derived(integration.last_sync_at ? formatDate(integration.last_sync_at) : null);

  /** @param {string} dateStr */
  function formatDate(dateStr) {
    try {
      return new Date(dateStr).toLocaleDateString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch { return dateStr; }
  }
</script>

<Card.Root class="group transition-shadow hover:shadow-md">
  <Card.Header>
    <div class="flex items-start justify-between">
      <div class="flex items-center gap-3">
        <div class="flex size-10 items-center justify-center rounded-lg bg-primary/10">
          <Plug class="size-5 text-primary" />
        </div>
        <div>
          <Card.Title class="text-sm">{integration.name || slug}</Card.Title>
          <Card.Description class="text-xs">{slug}</Card.Description>
        </div>
      </div>
      <IntegrationHealth status={integration.health_status || 'unknown'} />
    </div>
  </Card.Header>
  <Card.Content class="space-y-3">
    <div class="flex items-center gap-2">
      <Badge variant={integration.is_active ? 'default' : 'secondary'} class="text-xs">
        {integration.is_active ? 'Ativo' : 'Inativo'}
      </Badge>
      {#if integration.sync_status}
        <SyncStatusBadge status={integration.sync_status} />
      {/if}
    </div>
    {#if lastSync}
      <p class="text-muted-foreground flex items-center gap-1.5 text-xs">
        <RefreshCw class="size-3" />
        Último sync: {lastSync}
      </p>
    {/if}
  </Card.Content>
  <Card.Footer>
    <Button variant="outline" href="/settings/integrations/{slug}" class="w-full gap-2" size="sm">
      <Settings class="size-4" />
      Configurar
    </Button>
  </Card.Footer>
</Card.Root>
