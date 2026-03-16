<script>
  import { assistant } from '$lib/api.js';
  import { formatDate } from '$lib/utils/formatting.js';
  import { History, ChevronDown, ChevronRight, CheckCircle, XCircle, Clock, Loader, Bell, Zap, Megaphone } from '@lucide/svelte';

  let { targetType, targetId } = $props();

  let jobs = $state([]);
  let expanded = $state(false);
  let loading = $state(false);
  let loaded = $state(false);

  const STATUS_MAP = {
    completed: { icon: CheckCircle, class: 'text-emerald-600 dark:text-emerald-400' },
    failed: { icon: XCircle, class: 'text-red-600 dark:text-red-400' },
    pending: { icon: Clock, class: 'text-amber-600 dark:text-amber-400' },
    running: { icon: Loader, class: 'text-blue-600 dark:text-blue-400' },
    cancelled: { icon: XCircle, class: 'text-muted-foreground' },
  };

  const TYPE_MAP = {
    reminder: { label: 'Lembrete', icon: Bell },
    automation: { label: 'Automação', icon: Zap },
    campaign_step: { label: 'Campanha', icon: Megaphone },
  };

  async function toggle() {
    expanded = !expanded;
    if (expanded && !loaded) {
      await loadJobs();
    }
  }

  async function loadJobs() {
    loading = true;
    try {
      const result = await assistant.entityJobs(targetType, targetId);
      jobs = Array.isArray(result) ? result.slice(0, 10) : [];
      loaded = true;
    } catch {
      jobs = [];
      loaded = true;
    } finally {
      loading = false;
    }
  }
</script>

<div class="rounded-lg border">
  <button
    type="button"
    class="hover:bg-muted/50 flex w-full items-center justify-between px-4 py-3 transition-colors"
    onclick={toggle}
  >
    <div class="flex items-center gap-2">
      {#if expanded}
        <ChevronDown class="text-muted-foreground size-4" />
      {:else}
        <ChevronRight class="text-muted-foreground size-4" />
      {/if}
      <History class="size-4" />
      <span class="text-sm font-semibold">Histórico de Execuções</span>
      {#if loaded && jobs.length > 0}
        <span class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-300">
          {jobs.length}
        </span>
      {/if}
    </div>
  </button>

  {#if expanded}
    <div class="border-t px-4 py-3">
      {#if loading}
        <div class="flex items-center justify-center py-4">
          <Loader class="text-muted-foreground size-4 animate-spin" />
          <span class="text-muted-foreground ml-2 text-xs">Carregando...</span>
        </div>
      {:else if jobs.length === 0}
        <p class="text-muted-foreground py-3 text-center text-xs">
          Nenhuma execução registrada para esta entidade.
        </p>
      {:else}
        <div class="space-y-2">
          {#each jobs as job (job.id)}
            {@const statusInfo = STATUS_MAP[job.status] || STATUS_MAP.pending}
            {@const typeInfo = TYPE_MAP[job.job_type] || TYPE_MAP.automation}
            {@const StatusIcon = statusInfo.icon}
            {@const TypeIcon = typeInfo.icon}
            <div class="flex items-start gap-3 rounded-md border p-2.5">
              <StatusIcon class="mt-0.5 size-4 shrink-0 {statusInfo.class}" />
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5">
                  <TypeIcon class="text-muted-foreground size-3" />
                  <span class="text-xs font-medium">{typeInfo.label}</span>
                  {#if job.label}
                    <span class="text-muted-foreground truncate text-xs">— {job.label}</span>
                  {/if}
                </div>
                <div class="text-muted-foreground mt-0.5 flex items-center gap-2 text-[11px]">
                  <span>{formatDate(job.due_at || job.created_at)}</span>
                  <span class="rounded bg-muted px-1 py-0.5">{job.status}</span>
                </div>
                {#if job.error_message}
                  <p class="mt-1 truncate text-[11px] text-red-600 dark:text-red-400">{job.error_message}</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>
        <div class="mt-2 text-center">
          <a href="/autopilot?tab=runs" class="text-primary text-xs hover:underline">
            Ver todas as execuções →
          </a>
        </div>
      {/if}
    </div>
  {/if}
</div>
