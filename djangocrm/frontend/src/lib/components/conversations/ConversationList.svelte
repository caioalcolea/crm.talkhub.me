<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import ChannelBadge from '$lib/components/channels/ChannelBadge.svelte';
  import { User, Users, Clock, Loader2 } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} conversations
   * @property {string} [selected]
   * @property {(conv: any) => void} [onSelect]
   * @property {boolean} [isGroupView]
   * @property {boolean} [hasMore]
   * @property {boolean} [loadingMore]
   * @property {() => void} [onLoadMore]
   */

  /** @type {Props} */
  let { conversations = [], selected = '', onSelect, isGroupView = false, hasMore = false, loadingMore = false, onLoadMore } = $props();

  /** @type {HTMLDivElement|undefined} */
  let sentinel = $state();

  // IntersectionObserver for infinite scroll
  $effect(() => {
    if (!sentinel || !hasMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loadingMore) {
          onLoadMore?.();
        }
      },
      { rootMargin: '200px' }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

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

  /** Strip HTML tags for preview text */
  function stripHtml(text) {
    if (!text) return '';
    return text.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
  }
</script>

{#if conversations.length === 0}
  <div class="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
    {#if isGroupView}
      <Users class="mb-2 size-8 opacity-30" />
      <p class="text-sm">Nenhum grupo encontrado</p>
    {:else}
      <User class="mb-2 size-8 opacity-30" />
      <p class="text-sm">Nenhuma conversa encontrada</p>
    {/if}
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
        <div class="relative mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full {isGroupView || conv.is_group ? 'bg-indigo-100 dark:bg-indigo-950' : 'bg-muted'}">
          {#if isGroupView || conv.is_group}
            <Users class="size-5 text-indigo-600 dark:text-indigo-400" />
          {:else}
            <User class="size-5 text-muted-foreground" />
          {/if}
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

          {#if conv.contact_address}
            <p class="truncate text-[11px] text-muted-foreground/60">
              {conv.contact_address}
            </p>
          {/if}

          {#if conv.metadata_json?.email_subject}
            <p class="mt-0.5 truncate text-xs text-muted-foreground/60 italic">
              {conv.metadata_json.email_subject}
            </p>
          {/if}

          {#if conv.last_message}
            <p class="mt-0.5 truncate text-xs text-muted-foreground">
              {#if conv.last_message.direction === 'out'}
                <span class="text-muted-foreground/60">Você: </span>
              {/if}
              {stripHtml(conv.last_message.content)}
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

    <!-- Infinite scroll sentinel -->
    {#if hasMore}
      <div bind:this={sentinel} class="flex items-center justify-center py-4">
        {#if loadingMore}
          <Loader2 class="size-5 animate-spin text-muted-foreground" />
        {:else}
          <span class="text-xs text-muted-foreground">Carregando mais...</span>
        {/if}
      </div>
    {/if}
  </div>
{/if}
