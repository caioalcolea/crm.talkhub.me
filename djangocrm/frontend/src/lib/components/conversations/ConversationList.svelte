<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import ChannelBadge from '$lib/components/channels/ChannelBadge.svelte';
  import { User, Clock } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} conversations
   * @property {string} [selected]
   * @property {(conv: any) => void} [onSelect]
   */

  /** @type {Props} */
  let { conversations = [], selected = '', onSelect } = $props();

  /** @param {string} dateStr */
  function timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'agora';
    if (mins < 60) return `${mins}min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  }

  const statusColors = {
    open: 'bg-emerald-500',
    pending: 'bg-amber-500',
    resolved: 'bg-gray-400'
  };
</script>

{#if conversations.length === 0}
  <div class="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
    <p class="text-sm">Nenhuma conversa encontrada</p>
  </div>
{:else}
  <div class="divide-y">
    {#each conversations as conv (conv.id)}
      <button
        class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50
          {selected === conv.id ? 'bg-muted/80 border-l-2 border-primary' : ''}"
        onclick={() => onSelect?.(conv)}
      >
        <!-- Avatar -->
        <div class="relative mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full bg-muted">
          <User class="size-5 text-muted-foreground" />
          <div class="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full border-2 border-background {statusColors[conv.status] || 'bg-gray-400'}"></div>
        </div>

        <!-- Content -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between gap-2">
            <span class="truncate text-sm font-medium">{conv.contact_name || 'Sem nome'}</span>
            <span class="shrink-0 text-[11px] text-muted-foreground">
              {timeAgo(conv.last_message_at)}
            </span>
          </div>

          {#if conv.last_message}
            <p class="mt-0.5 truncate text-xs text-muted-foreground">
              {#if conv.last_message.direction === 'out'}
                <span class="text-muted-foreground/60">Você: </span>
              {/if}
              {conv.last_message.content}
            </p>
          {/if}

          <div class="mt-1.5 flex items-center gap-1.5">
            <ChannelBadge channelType={conv.channel} />
            <Badge variant="outline" class="text-[10px] px-1.5 py-0">
              {conv.status === 'open' ? 'Aberta' : conv.status === 'pending' ? 'Pendente' : 'Concluída'}
            </Badge>
          </div>
        </div>
      </button>
    {/each}
  </div>
{/if}
