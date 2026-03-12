<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import ChannelSelector from '$lib/components/channels/ChannelSelector.svelte';
  import { apiRequest } from '$lib/api.js';
  import { Send, Paperclip, Loader2, AlertTriangle } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} conversationId
   * @property {any[]} [channels]
   * @property {string} [currentChannel]
   * @property {string} [emailSubject]
   * @property {(msg: any) => void} [onMessageSent]
   */

  /** @type {Props} */
  let { conversationId, channels = [], currentChannel = '', emailSubject = '', onMessageSent } = $props();

  let content = $state('');
  let subject = $state(emailSubject);
  let selectedChannel = $state(currentChannel || '');
  let sending = $state(false);
  let error = $state('');

  /** Whether the current channel is email */
  let isEmail = $derived(
    selectedChannel === 'smtp_native' ||
    selectedChannel === 'email' ||
    currentChannel === 'smtp_native' ||
    currentChannel === 'email'
  );

  async function sendMessage() {
    const text = content.trim();
    if (!text || sending) return;
    if (!conversationId) {
      error = 'Nenhuma conversa selecionada';
      return;
    }

    sending = true;
    error = '';

    try {
      /** @type {Record<string, any>} */
      const body = {
        msg_type: 'text',
        content: text,
        channel_type: selectedChannel || undefined
      };

      if (isEmail && subject) {
        body.subject = subject;
      }

      const msg = await apiRequest(`/conversations/${conversationId}/messages/create/`, {
        method: 'POST',
        body
      });
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

  {#if isEmail}
    <div class="flex items-center gap-2">
      <span class="text-xs text-muted-foreground shrink-0">Assunto:</span>
      <Input
        type="text"
        placeholder="Assunto do email"
        bind:value={subject}
        class="h-7 text-sm"
        disabled={sending}
      />
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
        placeholder={isEmail ? "Escreva seu email..." : "Digite sua mensagem..."}
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
