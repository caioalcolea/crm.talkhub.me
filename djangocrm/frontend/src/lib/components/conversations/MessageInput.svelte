<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import ChannelSelector from '$lib/components/channels/ChannelSelector.svelte';
  import { Send, Paperclip, Loader2, AlertTriangle } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} conversationId
   * @property {any[]} [channels]
   * @property {string} [currentChannel]
   * @property {(msg: any) => void} [onMessageSent]
   */

  /** @type {Props} */
  let { conversationId, channels = [], currentChannel = '', onMessageSent } = $props();

  let content = $state('');
  let selectedChannel = $state(currentChannel || '');
  let sending = $state(false);
  let error = $state('');

  async function sendMessage() {
    const text = content.trim();
    if (!text || sending) return;

    sending = true;
    error = '';

    try {
      const res = await fetch(`/api/conversations/${conversationId}/messages/create/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          msg_type: 'text',
          content: text,
          channel_type: selectedChannel || undefined
        })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Erro ao enviar mensagem');
      }

      const msg = await res.json();
      content = '';
      onMessageSent?.(msg);
    } catch (e) {
      error = e.message || 'Erro ao enviar';
    } finally {
      sending = false;
    }
  }

  /** @param {KeyboardEvent} e */
  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
</script>

<div class="border-t px-4 py-3 space-y-2">
  {#if error}
    <div class="flex items-center gap-2 text-xs text-destructive">
      <AlertTriangle class="size-3.5" />
      {error}
    </div>
  {/if}

  <div class="flex items-end gap-2">
    <!-- Channel selector (compact) -->
    {#if channels.length > 1}
      <div class="w-36 shrink-0">
        <ChannelSelector
          {channels}
          value={selectedChannel}
          onSelect={(v) => selectedChannel = v}
          placeholder="Canal"
        />
      </div>
    {/if}

    <!-- Text area -->
    <div class="relative flex-1">
      <textarea
        class="w-full resize-none rounded-lg border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        rows="1"
        placeholder="Digite sua mensagem..."
        bind:value={content}
        onkeydown={handleKeydown}
        disabled={sending}
      ></textarea>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-1">
      <Button variant="ghost" size="icon" class="size-9" title="Anexar arquivo" disabled={sending}>
        <Paperclip class="size-4" />
      </Button>

      <Button
        size="icon"
        class="size-9"
        onclick={sendMessage}
        disabled={!content.trim() || sending}
        title="Enviar"
      >
        {#if sending}
          <Loader2 class="size-4 animate-spin" />
        {:else}
          <Send class="size-4" />
        {/if}
      </Button>
    </div>
  </div>
</div>
