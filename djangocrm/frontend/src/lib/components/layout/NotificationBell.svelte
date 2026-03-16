<script>
  import { Bell, Check, CheckCheck, AlertTriangle, CircleCheck, Info, Loader } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import { notificationStore } from '$lib/stores/notifications.svelte.js';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';

  let open = $state(false);

  onMount(() => {
    notificationStore.startPolling();
    return () => notificationStore.stopPolling();
  });

  // Load full list when popover opens
  $effect(() => {
    if (open && browser) {
      notificationStore.loadNotifications({ limit: 10 });
    }
  });

  function getIcon(type) {
    if (type === 'job_completed') return CircleCheck;
    if (type === 'job_failed') return AlertTriangle;
    if (type === 'approval_pending') return Bell;
    return Info;
  }

  function getIconColor(type) {
    if (type === 'job_completed') return 'text-green-500';
    if (type === 'job_failed') return 'text-red-500';
    if (type === 'approval_pending') return 'text-amber-500';
    return 'text-blue-500';
  }

  function timeAgo(dateStr) {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'agora';
    if (mins < 60) return `${mins}min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  }
</script>

<Popover.Root bind:open>
  <Popover.Trigger>
    <button
      class="text-muted-foreground hover:text-foreground hover:bg-accent relative flex size-9 items-center justify-center rounded-lg transition-colors"
      aria-label="Notificações"
    >
      <Bell class="size-5" />
      {#if notificationStore.unreadCount > 0}
        <span class="absolute -top-0.5 -right-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
          {notificationStore.unreadCount > 9 ? '9+' : notificationStore.unreadCount}
        </span>
      {/if}
    </button>
  </Popover.Trigger>
  <Popover.Content align="end" class="w-80 p-0">
    <!-- Header -->
    <div class="flex items-center justify-between border-b px-4 py-2.5">
      <h3 class="text-sm font-semibold">Notificações</h3>
      {#if notificationStore.unreadCount > 0}
        <button
          onclick={() => notificationStore.markAllRead()}
          class="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
        >
          <CheckCheck class="size-3" />
          Marcar todas
        </button>
      {/if}
    </div>

    <!-- List -->
    <div class="max-h-80 overflow-y-auto">
      {#if notificationStore.isLoading && notificationStore.notifications.length === 0}
        <div class="flex items-center justify-center py-8">
          <Loader class="size-5 animate-spin text-gray-400" />
        </div>
      {:else if notificationStore.notifications.length === 0}
        <div class="flex flex-col items-center gap-2 py-8 text-gray-400">
          <Bell class="size-6" />
          <p class="text-xs">Nenhuma notificação</p>
        </div>
      {:else}
        {#each notificationStore.notifications as notif (notif.id)}
          {@const IconComp = getIcon(notif.type)}
          {@const iconColor = getIconColor(notif.type)}
          <div
            class="flex items-start gap-3 border-b px-4 py-3 last:border-b-0 {notif.read_at ? 'bg-white' : 'bg-indigo-50/50'}"
          >
            <div class="mt-0.5 shrink-0 {iconColor}">
              <IconComp class="size-4" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-xs font-medium text-gray-900">{notif.title}</p>
              {#if notif.body}
                <p class="mt-0.5 line-clamp-2 text-[11px] text-gray-500">{notif.body}</p>
              {/if}
              <p class="mt-1 text-[10px] text-gray-400">{timeAgo(notif.created_at)}</p>
            </div>
            {#if !notif.read_at}
              <button
                onclick={() => notificationStore.markAsRead(notif.id)}
                class="mt-0.5 shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                title="Marcar como lida"
              >
                <Check class="size-3" />
              </button>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    <!-- Footer -->
    {#if notificationStore.notifications.length > 0}
      <div class="border-t px-4 py-2 text-center">
        <a
          href="/autopilot?tab=runs"
          class="text-xs text-indigo-600 hover:text-indigo-800"
          onclick={() => { open = false; }}
        >
          Ver todas
        </a>
      </div>
    {/if}
  </Popover.Content>
</Popover.Root>
