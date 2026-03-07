<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Switch } from '$lib/components/ui/switch/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { RefreshCw, Loader2 } from '@lucide/svelte';
  import SyncStatusBadge from './SyncStatusBadge.svelte';

  /**
   * @typedef {Object} Props
   * @property {boolean} syncEnabled
   * @property {any[]} modules - Sync modules with name, enabled, last_sync_at
   * @property {any[]} recentLogs
   * @property {() => void} [onSyncNow]
   * @property {(mod: string, enabled: boolean) => void} [onToggleModule]
   * @property {boolean} [syncing]
   */

  /** @type {Props} */
  let { syncEnabled = false, modules = [], recentLogs = [], onSyncNow, onToggleModule, syncing = false } = $props();
</script>

<div class="space-y-4">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      <Switch checked={syncEnabled} />
      <span class="text-sm font-medium">Sincronização automática</span>
    </div>
    {#if onSyncNow}
      <Button variant="outline" size="sm" onclick={onSyncNow} disabled={syncing} class="gap-2">
        <RefreshCw class="size-4 {syncing ? 'animate-spin' : ''}" />
        {syncing ? 'Sincronizando...' : 'Sincronizar Agora'}
      </Button>
    {/if}
  </div>

  <!-- Module toggles -->
  {#if modules.length > 0}
    <div class="space-y-2">
      <p class="text-muted-foreground text-xs font-medium uppercase tracking-wider">Módulos</p>
      {#each modules as mod (mod.name)}
        <div class="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
          <span class="text-sm">{mod.label || mod.name}</span>
          <div class="flex items-center gap-2">
            {#if mod.last_sync_at}
              <span class="text-muted-foreground text-xs">{new Date(mod.last_sync_at).toLocaleString('pt-BR')}</span>
            {/if}
            {#if onToggleModule}
              <Switch checked={mod.enabled} onCheckedChange={(v) => onToggleModule(mod.name, v)} />
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Recent logs -->
  {#if recentLogs.length > 0}
    <div class="space-y-2">
      <p class="text-muted-foreground text-xs font-medium uppercase tracking-wider">Últimos Logs</p>
      <div class="max-h-64 overflow-y-auto space-y-1">
        {#each recentLogs.slice(0, 50) as log}
          <div class="flex items-center gap-2 text-xs px-2 py-1.5 rounded bg-muted/30">
            <SyncStatusBadge status={log.status || 'completed'} />
            <span class="flex-1 truncate">{log.message || log.operation}</span>
            <span class="text-muted-foreground shrink-0">{new Date(log.created_at).toLocaleString('pt-BR')}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
