<script>
  import { assistant } from '$lib/api.js';
  import { Bell, Zap, Megaphone } from '@lucide/svelte';

  let { taskId } = $props();

  let links = $state([]);
  let loaded = $state(false);

  const SOURCE_MAP = {
    'assistant.reminderpolicy': { label: 'Gerada por lembrete', icon: Bell, tab: 'reminders', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' },
    'automations.automation': { label: 'Gerada por automação', icon: Zap, tab: 'rules', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' },
    'campaigns.campaign': { label: 'Gerada por campanha', icon: Megaphone, tab: 'campaigns', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400' },
  };

  $effect(() => {
    if (taskId && !loaded) {
      loaded = true;
      assistant.taskLinks({ task_id: taskId }).then(result => {
        if (Array.isArray(result)) links = result;
      }).catch(() => {});
    }
  });
</script>

{#if links.length > 0}
  <div class="mb-3 flex flex-wrap gap-2">
    {#each links as link}
      {@const info = SOURCE_MAP[link.source_type] || SOURCE_MAP['automations.automation']}
      {@const Icon = info.icon}
      <a
        href="/autopilot?tab={info.tab}"
        class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors hover:opacity-80 {info.color}"
      >
        <Icon class="size-3" />
        {info.label}{link.source_name ? `: ${link.source_name}` : ''}
      </a>
    {/each}
  </div>
{/if}
