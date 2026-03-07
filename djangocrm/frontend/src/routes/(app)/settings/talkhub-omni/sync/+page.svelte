<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { RefreshCw, Users, Tag, Layers, Bot, Zap, CheckCircle, XCircle, Clock, Loader2 } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let syncHistory = $derived(data.syncHistory || []);
  let activeJobId = $state(/** @type {string | null} */ (null));
  let activeJob = $state(/** @type {any} */ (null));
  let isSyncing = $state(/** @type {Record<string, boolean>} */ ({}));

  $effect(() => {
    if (form?.syncStarted) {
      toast.success(`Sync de ${form.syncType} iniciado`);
      activeJobId = form.jobId;
      startPolling();
    }
    if (form?.syncError) toast.error(form.syncError);
  });

  let pollInterval = $state(/** @type {ReturnType<typeof setInterval> | null} */ (null));

  function startPolling() {
    stopPolling();
    pollInterval = setInterval(async () => {
      if (!activeJobId) { stopPolling(); return; }
      try {
        const resp = await fetch(`/api/talkhub-sync-poll?job=${activeJobId}`);
        const data = await resp.json();
        activeJob = data.job;
        if (activeJob && (activeJob.status === 'COMPLETED' || activeJob.status === 'FAILED' || activeJob.status === 'CANCELLED')) {
          stopPolling();
          if (activeJob.status === 'COMPLETED') {
            toast.success(`Sync concluído: ${activeJob.imported_count} importados, ${activeJob.updated_count} atualizados`);
          } else if (activeJob.status === 'FAILED') {
            toast.error('Sync falhou');
          }
          isSyncing = {};
        }
      } catch {
        /* ignore poll errors */
      }
    }, 3000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  /** @param {string} dateStr */
  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('pt-BR', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } catch { return dateStr; }
  }

  /** @param {string} status */
  function statusColor(status) {
    switch (status) {
      case 'COMPLETED': return 'border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400';
      case 'FAILED': return 'border-red-200 bg-red-100 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400';
      case 'IN_PROGRESS': return 'border-blue-200 bg-blue-100 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400';
      case 'PENDING': return 'border-amber-200 bg-amber-100 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400';
      default: return '';
    }
  }

  const syncCards = [
    { type: 'contacts', label: 'Contatos', desc: 'Subscribers ↔ Contatos', icon: Users, action: 'syncContacts' },
    { type: 'kanbans', label: 'Kanban', desc: 'Ticket Lists ↔ Boards', icon: Layers, action: 'syncKanbans' },
    { type: 'users', label: 'Usuários', desc: 'Team Members → Profiles', icon: Users, action: 'syncUsers' },
  ];
</script>

<svelte:head>
  <title>Sync TalkHub Omni - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Sincronização TalkHub Omni" subtitle="Gerencie a sincronização de dados" />

<div class="mx-auto max-w-4xl space-y-6 p-6 md:p-8">
  <!-- Sync All button -->
  <div class="flex items-center justify-between">
    <p class="text-muted-foreground text-sm">
      Sync automático ativo: Contatos (5min), Tags (10min), Kanban (15min)
    </p>
    <form method="POST" action="?/syncAll" use:enhance={() => {
      isSyncing = { all: true };
      return async ({ update }) => { await update(); };
    }}>
      <Button type="submit" disabled={!!Object.keys(isSyncing).length} class="gap-2">
        {#if isSyncing.all}
          <Loader2 class="size-4 animate-spin" />
        {:else}
          <Zap class="size-4" />
        {/if}
        Sync Completo
      </Button>
    </form>
  </div>

  <!-- Active Job Progress -->
  {#if activeJob && (activeJob.status === 'PENDING' || activeJob.status === 'IN_PROGRESS')}
    <Card.Root class="border-blue-200 dark:border-blue-800">
      <Card.Content class="pt-6">
        <div class="flex items-center gap-3">
          <Loader2 class="size-5 animate-spin text-blue-500" />
          <div class="flex-1">
            <p class="text-foreground text-sm font-medium">
              Sincronizando {activeJob.sync_type}...
            </p>
            <div class="mt-2 h-2 w-full overflow-hidden rounded-full bg-blue-100 dark:bg-blue-950">
              {#if activeJob.total_records > 0}
                {@const pct = Math.round(((activeJob.imported_count + activeJob.updated_count + activeJob.skipped_count) / activeJob.total_records) * 100)}
                <div class="h-full rounded-full bg-blue-500 transition-all" style="width: {pct}%"></div>
              {:else}
                <div class="h-full w-1/3 animate-pulse rounded-full bg-blue-500"></div>
              {/if}
            </div>
            <p class="text-muted-foreground mt-1 text-xs">
              {activeJob.imported_count} importados, {activeJob.updated_count} atualizados, {activeJob.skipped_count} ignorados
              {#if activeJob.error_count > 0}, {activeJob.error_count} erros{/if}
            </p>
          </div>
        </div>
      </Card.Content>
    </Card.Root>
  {/if}

  <!-- Sync Cards Grid -->
  <div class="grid gap-4 sm:grid-cols-2">
    {#each syncCards as card}
      <Card.Root>
        <Card.Header class="pb-3">
          <div class="flex items-center gap-3">
            <div class="flex size-9 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-950">
              <card.icon class="size-4 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <Card.Title class="text-base">{card.label}</Card.Title>
              <Card.Description class="text-xs">{card.desc}</Card.Description>
            </div>
          </div>
        </Card.Header>
        <Card.Content>
          {@const lastJob = syncHistory.find((/** @type {any} */ j) => j.sync_type === card.type)}
          {#if lastJob}
            <div class="text-muted-foreground mb-3 space-y-1 text-xs">
              <p>Último: {formatDate(lastJob.completed_at || lastJob.created_at)}</p>
              <p>{lastJob.imported_count} imp. / {lastJob.updated_count} atua. / {lastJob.error_count} err.</p>
            </div>
          {/if}
          <form method="POST" action="?/{card.action}" use:enhance={() => {
            isSyncing = { [card.type]: true };
            return async ({ update }) => { await update(); };
          }}>
            <Button type="submit" variant="outline" size="sm" class="w-full gap-2" disabled={!!Object.keys(isSyncing).length}>
              {#if isSyncing[card.type]}
                <Loader2 class="size-3 animate-spin" />
              {:else}
                <RefreshCw class="size-3" />
              {/if}
              Sync Agora
            </Button>
          </form>
        </Card.Content>
      </Card.Root>
    {/each}
  </div>

  <!-- Sync History -->
  <Card.Root>
    <Card.Header>
      <Card.Title class="text-base">Histórico de Sync</Card.Title>
    </Card.Header>
    <Card.Content>
      {#if syncHistory.length === 0}
        <p class="text-muted-foreground py-4 text-center text-sm">Nenhum sync realizado ainda.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-muted-foreground border-b text-left text-xs">
                <th class="pb-2 font-medium">Tipo</th>
                <th class="pb-2 font-medium">Status</th>
                <th class="pb-2 font-medium">Importados</th>
                <th class="pb-2 font-medium">Atualizados</th>
                <th class="pb-2 font-medium">Erros</th>
                <th class="pb-2 font-medium">Data</th>
              </tr>
            </thead>
            <tbody>
              {#each syncHistory.slice(0, 20) as job}
                <tr class="border-b last:border-0">
                  <td class="py-2 capitalize">{job.sync_type}</td>
                  <td class="py-2">
                    <Badge class={statusColor(job.status)}>{job.status}</Badge>
                  </td>
                  <td class="py-2">{job.imported_count}</td>
                  <td class="py-2">{job.updated_count}</td>
                  <td class="py-2">{job.error_count}</td>
                  <td class="text-muted-foreground py-2 text-xs">{formatDate(job.created_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </Card.Content>
  </Card.Root>
</div>
