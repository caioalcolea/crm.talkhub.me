<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import ChannelBadge from '$lib/components/channels/ChannelBadge.svelte';
  import ContactAutocomplete from '$lib/components/contacts/ContactAutocomplete.svelte';
  import MessageBubble from './MessageBubble.svelte';
  import { toast } from 'svelte-sonner';
  import { User, Bot, Pause, Play, UserPlus, UserMinus, Loader2, ChevronUp, Link, Unlink } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any} conversation
   * @property {any[]} messages
   * @property {boolean} [loading]
   * @property {((contact: any) => void)} [onContactChanged]
   */

  /** @type {Props} */
  let { conversation, messages = [], loading = false, onContactChanged } = $props();

  let loadingMore = $state(false);
  let timelineEl = $state(null);
  let showContactPicker = $state(false);
  /** @type {any} */
  let pickerContact = $state(null);
  let savingContact = $state(false);

  // Auto-scroll to bottom when messages change
  $effect(() => {
    if (messages.length && timelineEl) {
      requestAnimationFrame(() => {
        timelineEl.scrollTop = timelineEl.scrollHeight;
      });
    }
  });

  async function loadOlderMessages() {
    loadingMore = true;
    // TODO: implement cursor-based pagination
    loadingMore = false;
  }

  async function assignAgent() {
    // TODO: open agent picker modal
  }

  async function unassignAgent() {
    try {
      await fetch(`/api/conversations/${conversation.id}/unassign/`, { method: 'POST' });
    } catch (e) {
      console.error('Erro ao desatribuir agente:', e);
    }
  }

  /** @param {'pause' | 'resume'} action */
  async function toggleBot(action) {
    try {
      await fetch(`/api/conversations/${conversation.id}/bot/${action}/`, { method: 'POST' });
    } catch (e) {
      console.error(`Erro ao ${action} bot:`, e);
    }
  }

  /** @param {string} newStatus */
  async function updateStatus(newStatus) {
    try {
      await fetch(`/api/conversations/${conversation.id}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
    } catch (e) {
      console.error('Erro ao atualizar status:', e);
    }
  }

  /** @param {any} contact */
  async function handleContactSelected(contact) {
    savingContact = true;
    try {
      const { apiRequest } = await import('$lib/api.js');
      await apiRequest(`/conversations/${conversation.id}/`, {
        method: 'PATCH',
        body: { contact: contact.id }
      });
      toast.success('Contato vinculado à conversa');
      showContactPicker = false;
      pickerContact = null;
      onContactChanged?.(contact);
    } catch (err) {
      toast.error('Erro ao vincular contato');
      console.error('Erro ao vincular contato:', err);
    } finally {
      savingContact = false;
    }
  }

  async function unlinkContact() {
    // Conversation.contact is a required FK (on_delete=CASCADE), so we can't set it to null.
    // Just close the picker if open.
    showContactPicker = false;
    pickerContact = null;
  }
</script>

<div class="flex flex-1 flex-col overflow-hidden">
  <!-- Header -->
  <div class="flex items-center justify-between border-b px-4 py-3">
    <div class="flex items-center gap-3">
      <div class="flex size-9 items-center justify-center rounded-full bg-muted">
        <User class="size-4 text-muted-foreground" />
      </div>
      <div>
        {#if showContactPicker}
          <div class="w-64">
            <ContactAutocomplete
              bind:selectedContact={pickerContact}
              onSelect={handleContactSelected}
              placeholder="Buscar contato..."
              class="text-sm"
            />
          </div>
          <button
            type="button"
            class="mt-1 text-[11px] text-muted-foreground hover:text-foreground"
            onclick={() => { showContactPicker = false; pickerContact = null; }}
          >
            Cancelar
          </button>
        {:else}
          <div class="flex items-center gap-1.5">
            <p class="text-sm font-medium">{conversation.contact_name || 'Sem contato'}</p>
            <button
              type="button"
              onclick={() => (showContactPicker = true)}
              class="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              title={conversation.contact_name ? 'Alterar contato' : 'Vincular contato'}
            >
              <Link class="size-3.5" />
            </button>
          </div>
          <div class="flex items-center gap-2">
            <ChannelBadge channel={conversation.channel} size="xs" />
            {#if conversation.assigned_to_name}
              <span class="text-[11px] text-muted-foreground">Agente: {conversation.assigned_to_name}</span>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <div class="flex items-center gap-1.5">
      <Select.Root type="single" value={conversation.status} onValueChange={updateStatus}>
        <Select.Trigger class="h-8 w-28 text-xs">
          {conversation.status === 'open' ? 'Aberta' : conversation.status === 'pending' ? 'Pendente' : 'Concluída'}
        </Select.Trigger>
        <Select.Content>
          <Select.Item value="open">Aberta</Select.Item>
          <Select.Item value="pending">Pendente</Select.Item>
          <Select.Item value="resolved">Concluída</Select.Item>
        </Select.Content>
      </Select.Root>

      <Button variant="ghost" size="icon" class="size-8" onclick={assignAgent} title="Atribuir agente">
        <UserPlus class="size-4" />
      </Button>

      {#if conversation.assigned_to}
        <Button variant="ghost" size="icon" class="size-8" onclick={unassignAgent} title="Desatribuir agente">
          <UserMinus class="size-4" />
        </Button>
      {/if}

      {#if conversation.omni_user_ns}
        <Button variant="ghost" size="icon" class="size-8" onclick={() => toggleBot('pause')} title="Pausar bot">
          <Pause class="size-4" />
        </Button>
        <Button variant="ghost" size="icon" class="size-8" onclick={() => toggleBot('resume')} title="Retomar bot">
          <Play class="size-4" />
        </Button>
      {/if}
    </div>
  </div>

  <!-- Messages timeline -->
  <div class="flex-1 overflow-y-auto px-4 py-3 space-y-1" bind:this={timelineEl}>
    {#if loadingMore}
      <div class="flex justify-center py-2">
        <Loader2 class="size-4 animate-spin text-muted-foreground" />
      </div>
    {:else if messages.length >= 50}
      <div class="flex justify-center py-2">
        <Button variant="ghost" size="sm" class="gap-1.5 text-xs" onclick={loadOlderMessages}>
          <ChevronUp class="size-3.5" />
          Carregar anteriores
        </Button>
      </div>
    {/if}

    {#if loading}
      <div class="flex flex-1 items-center justify-center py-16">
        <Loader2 class="size-6 animate-spin text-muted-foreground" />
      </div>
    {:else if messages.length === 0}
      <div class="flex flex-1 items-center justify-center py-16 text-muted-foreground">
        <p class="text-sm">Nenhuma mensagem nesta conversa</p>
      </div>
    {:else}
      {#each messages as msg (msg.id)}
        <MessageBubble message={msg} />
      {/each}
    {/if}
  </div>
</div>
