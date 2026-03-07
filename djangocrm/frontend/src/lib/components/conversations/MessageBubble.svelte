<script>
  import MediaRenderer from './MediaRenderer.svelte';
  import { Bot, User, Lock, Info } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any} message
   */

  /** @type {Props} */
  let { message } = $props();

  /** @param {string} dateStr */
  function formatTime(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  const directionConfig = {
    in: {
      align: 'items-start',
      bubble: 'bg-muted text-foreground rounded-tl-sm',
      icon: User,
      showSender: true
    },
    out: {
      align: 'items-end',
      bubble: 'bg-blue-500 text-white rounded-tr-sm',
      icon: Bot,
      showSender: false
    },
    agent: {
      align: 'items-end',
      bubble: 'bg-emerald-500 text-white rounded-tr-sm',
      icon: User,
      showSender: true
    },
    note: {
      align: 'items-center',
      bubble: 'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-200 rounded-lg border border-amber-200 dark:border-amber-800',
      icon: Lock,
      showSender: false
    },
    system: {
      align: 'items-center',
      bubble: '',
      icon: Info,
      showSender: false
    }
  };

  let config = $derived(directionConfig[message.direction] || directionConfig.in);
</script>

{#if message.direction === 'system'}
  <!-- System message: centered small text -->
  <div class="flex justify-center py-1">
    <span class="text-[11px] text-muted-foreground italic">{message.content}</span>
  </div>
{:else if message.direction === 'note'}
  <!-- Note: centered with lock icon -->
  <div class="flex justify-center py-1">
    <div class="flex items-start gap-2 max-w-md px-3 py-2 {config.bubble}">
      <Lock class="size-3.5 mt-0.5 shrink-0 opacity-60" />
      <div>
        <MediaRenderer msgType={message.msg_type} content={message.content} mediaUrl={message.media_url} metadata={message.metadata_json} />
        <span class="text-[10px] opacity-60 mt-1 block">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  </div>
{:else}
  <!-- Regular message bubble -->
  <div class="flex flex-col {config.align} py-0.5">
    {#if config.showSender && message.sender_name}
      <span class="text-[10px] text-muted-foreground mb-0.5 px-1">
        {message.sender_name}
      </span>
    {/if}
    <div class="max-w-[70%] rounded-2xl px-3 py-2 {config.bubble}">
      <MediaRenderer msgType={message.msg_type} content={message.content} mediaUrl={message.media_url} metadata={message.metadata_json} />
      <div class="flex items-center justify-end gap-1 mt-1">
        <span class="text-[10px] opacity-60">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  </div>
{/if}
