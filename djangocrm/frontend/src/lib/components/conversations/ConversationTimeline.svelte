<script>
  import { goto } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import ChannelBadge from '$lib/components/channels/ChannelBadge.svelte';
  import ContactAutocomplete from '$lib/components/contacts/ContactAutocomplete.svelte';
  import MessageBubble from './MessageBubble.svelte';
  import { toast } from 'svelte-sonner';
  import { apiRequest } from '$lib/api.js';
  import { User, Bot, Pause, Play, UserPlus, UserMinus, Loader2, ChevronUp, Link, Unlink, Target, Sparkles, Check } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any} conversation
   * @property {any[]} messages
   * @property {boolean} [loading]
   * @property {((contact: any) => void)} [onContactChanged]
   * @property {((conversation: any) => void)} [onConversationChanged]
   * @property {import('svelte').Snippet} [headerActions]
   */

  /** @type {Props} */
  let { conversation, messages = [], loading = false, onContactChanged, onConversationChanged, headerActions } = $props();

  let loadingMore = $state(false);
  let timelineEl = $state(null);
  let showContactPicker = $state(false);
  /** @type {any} */
  let pickerContact = $state(null);
  let savingContact = $state(false);

  // Agent picker state
  let showAgentPicker = $state(false);
  /** @type {any[]} */
  let agents = $state([]);
  let loadingAgents = $state(false);

  // Auto-scroll to bottom when messages change
  $effect(() => {
    if (messages.length && timelineEl) {
      requestAnimationFrame(() => {
        timelineEl.scrollTop = timelineEl.scrollHeight;
      });
    }
  });

  // Load agents when popover opens
  $effect(() => {
    if (showAgentPicker && agents.length === 0) {
      loadAgents();
    }
  });

  async function loadOlderMessages() {
    loadingMore = true;
    // TODO: implement cursor-based pagination
    loadingMore = false;
  }

  async function loadAgents() {
    loadingAgents = true;
    try {
      const data = await apiRequest('/users/get-teams-and-users/');
      agents = data.profiles || [];
    } catch (e) {
      toast.error('Erro ao carregar agentes');
    } finally {
      loadingAgents = false;
    }
  }

  /** @param {any} agent */
  async function selectAgent(agent) {
    try {
      await apiRequest(`/conversations/${conversation.id}/assign/`, {
        method: 'POST',
        body: { profile_id: agent.id }
      });
      const fullName = [agent.user_details?.first_name, agent.user_details?.last_name].filter(Boolean).join(' ') || agent.user_details?.email || '';
      const updated = { ...conversation, assigned_to: agent.id, assigned_to_name: fullName };
      toast.success('Agente atribuído');
      showAgentPicker = false;
      onConversationChanged?.(updated);
    } catch (e) {
      toast.error('Erro ao atribuir agente');
    }
  }

  async function unassignAgent() {
    try {
      await apiRequest(`/conversations/${conversation.id}/unassign/`, { method: 'POST' });
      const updated = { ...conversation, assigned_to: null, assigned_to_name: null };
      toast.success('Agente desatribuído');
      onConversationChanged?.(updated);
    } catch (e) {
      toast.error('Erro ao desatribuir agente');
    }
  }

  /** @param {'pause' | 'resume'} action */
  async function toggleBot(action) {
    try {
      await apiRequest(`/conversations/${conversation.id}/bot/${action}/`, { method: 'POST' });
    } catch (e) {
      console.error(`Erro ao ${action} bot:`, e);
    }
  }

  /** @param {string} newStatus */
  async function updateStatus(newStatus) {
    try {
      await apiRequest(`/conversations/${conversation.id}/`, {
        method: 'PATCH',
        body: { status: newStatus }
      });
      onConversationChanged?.({ ...conversation, status: newStatus });
    } catch (e) {
      console.error('Erro ao atualizar status:', e);
    }
  }

  /** @param {any} contact */
  async function handleContactSelected(contact) {
    savingContact = true;
    try {
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
            <ChannelBadge channelType={conversation.channel} />
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

      <!-- Agent picker popover -->
      <Popover.Root bind:open={showAgentPicker}>
        <Popover.Trigger>
          {#snippet child({ props })}
            <Button {...props} variant="ghost" size="icon" class="size-8" title="Atribuir agente">
              <UserPlus class="size-4" />
            </Button>
          {/snippet}
        </Popover.Trigger>
        <Popover.Content class="w-56 p-1" align="end">
          {#if loadingAgents}
            <div class="flex justify-center py-3">
              <Loader2 class="size-4 animate-spin text-muted-foreground" />
            </div>
          {:else if agents.length === 0}
            <p class="px-3 py-2 text-center text-xs text-muted-foreground">Nenhum agente encontrado</p>
          {:else}
            <div class="max-h-48 overflow-y-auto">
              {#each agents as agent (agent.id)}
                <button
                  type="button"
                  class="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground"
                  onclick={() => selectAgent(agent)}
                >
                  <User class="size-4 shrink-0 text-muted-foreground" />
                  <span class="truncate">
                    {[agent.user_details?.first_name, agent.user_details?.last_name].filter(Boolean).join(' ') || agent.user_details?.email || 'Sem nome'}
                  </span>
                  {#if conversation.assigned_to === agent.id}
                    <Check class="ml-auto size-3.5 shrink-0 text-primary" />
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </Popover.Content>
      </Popover.Root>

      {#if conversation.assigned_to}
        <Button variant="ghost" size="icon" class="size-8" onclick={unassignAgent} title="Desatribuir agente">
          <UserMinus class="size-4" />
        </Button>
      {/if}

      <!-- Criar Oportunidade (→ /leads) -->
      <Button
        variant="ghost"
        size="icon"
        class="size-8"
        onclick={() => goto(`/leads?action=create${conversation.contact ? `&contactId=${conversation.contact}` : ''}`)}
        title="Criar Oportunidade"
      >
        <Target class="size-4" />
      </Button>

      <!-- Criar Negócio (→ /opportunities) -->
      <Button
        variant="ghost"
        size="icon"
        class="size-8"
        onclick={() => goto(`/opportunities?action=create${conversation.contact ? `&contactId=${conversation.contact}` : ''}`)}
        title="Criar Negócio"
      >
        <Sparkles class="size-4" />
      </Button>

      {#if headerActions}
        {@render headerActions()}
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
