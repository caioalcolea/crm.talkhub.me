<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Sheet from '$lib/components/ui/sheet/index.js';
  import ConversationTimeline from './ConversationTimeline.svelte';
  import MessageInput from './MessageInput.svelte';
  import { X, Loader2, MessageSquare } from '@lucide/svelte';
  import { apiRequest, getCurrentUser } from '$lib/api.js';

  /**
   * @typedef {Object} Props
   * @property {string} contactId
   * @property {boolean} [open]
   * @property {(open: boolean) => void} [onOpenChange]
   */

  /** @type {Props} */
  let { contactId, open = false, onOpenChange } = $props();

  const currentUser = $derived(getCurrentUser());
  const isAdmin = $derived(currentUser?.role === 'ADMIN' || currentUser?.is_organization_admin || currentUser?.is_superuser);

  /** @type {any} */
  let conversation = $state(null);
  /** @type {any[]} */
  let messages = $state([]);
  /** @type {any[]} */
  let channels = $state([]);
  let loading = $state(false);

  $effect(() => {
    if (open && contactId) {
      loadConversation();
    }
  });

  async function loadConversation() {
    loading = true;
    try {
      // Fetch conversations for this contact
      const convs = await apiRequest(`/contacts/${contactId}/conversations/`);
      if (convs && convs.length > 0) {
        conversation = convs[0]; // Most recent
        // Load messages
        const data = await apiRequest(`/conversations/${conversation.id}/messages/`);
        messages = data?.results || data || [];
      }
      // Load channels
      const chData = await apiRequest('/channels/');
      channels = chData?.results || chData || [];
    } catch (e) {
      console.error('Erro ao carregar conversa:', e);
    } finally {
      loading = false;
    }
  }

  /** @param {any} msg */
  function onMessageSent(msg) {
    messages = [...messages, msg];
  }
</script>

<Sheet.Root {open} {onOpenChange}>
  <Sheet.Content side="right" class="flex w-full max-w-lg flex-col p-0 sm:max-w-xl">
    <Sheet.Header class="border-b px-4 py-3">
      <Sheet.Title class="flex items-center gap-2 text-sm">
        <MessageSquare class="size-4" />
        Conversa
      </Sheet.Title>
    </Sheet.Header>

    <div class="flex flex-1 flex-col overflow-hidden">
      {#if loading}
        <div class="flex flex-1 items-center justify-center">
          <Loader2 class="size-6 animate-spin text-muted-foreground" />
        </div>
      {:else if conversation}
        <ConversationTimeline
          {conversation}
          {messages}
          {isAdmin}
          onConversationChanged={(updated) => {
            if (updated.is_deleted || updated._permanentlyDeleted) {
              conversation = null;
            } else {
              conversation = updated;
            }
          }}
        />
        <MessageInput
          conversationId={conversation.id}
          {channels}
          currentChannel={conversation.channel}
          {onMessageSent}
        />
      {:else}
        <div class="flex flex-1 items-center justify-center text-muted-foreground">
          <div class="text-center">
            <MessageSquare class="mx-auto mb-3 size-10 opacity-30" />
            <p class="text-sm">Nenhuma conversa encontrada para este contato</p>
          </div>
        </div>
      {/if}
    </div>
  </Sheet.Content>
</Sheet.Root>
