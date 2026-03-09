<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onDestroy } from 'svelte';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { MessageSquare, Search, Filter, RefreshCw, PanelRight } from '@lucide/svelte';
  import ConversationList from '$lib/components/conversations/ConversationList.svelte';
  import ConversationTimeline from '$lib/components/conversations/ConversationTimeline.svelte';
  import MessageInput from '$lib/components/conversations/MessageInput.svelte';
  import { RelatedEntitiesPanel } from '$lib/components/ui/related-entities/index.js';
  import { apiRequest } from '$lib/api.js';
  import { toast } from 'svelte-sonner';

  /** @type {{ data: any }} */
  let { data } = $props();

  let conversations = $state(data.conversations || []);
  let channels = $derived(data.channels || []);
  let filters = $derived(data.filters || {});
  let showContextPanel = $state(false);

  /** @type {any} */
  let selectedConversation = $state(null);
  /** @type {any[]} */
  let messages = $state([]);
  let loadingMessages = $state(false);
  let searchQuery = $state('');
  let refreshing = $state(false);
  let lastPollTime = $state(new Date().toISOString());

  // Sync conversations when data changes (e.g. from server-side navigation)
  $effect(() => {
    conversations = data.conversations || [];
  });

  $effect(() => {
    if (data.error) toast.error(data.error);
  });

  $effect(() => {
    if (data.filters?.search) searchQuery = data.filters.search;
  });

  // Fast poll for real-time updates (every 5s)
  const pollInterval = setInterval(async () => {
    await pollUpdates();
  }, 5000);

  // Full refresh every 60s as fallback
  const fullRefreshInterval = setInterval(async () => {
    await refreshConversations(true);
  }, 60000);

  onDestroy(() => {
    clearInterval(pollInterval);
    clearInterval(fullRefreshInterval);
  });

  /**
   * Lightweight poll — only fetches conversations/messages updated since last poll.
   */
  async function pollUpdates() {
    try {
      const params = new URLSearchParams({ since: lastPollTime });
      if (selectedConversation) params.set('conversation_id', selectedConversation.id);

      const updates = await apiRequest(`/conversations/updates/?${params.toString()}`);
      if (!updates || updates.error) return;

      // Update server time for next poll
      if (updates.server_time) lastPollTime = updates.server_time;

      // Merge updated conversations into the list
      if (updates.conversations?.length > 0) {
        const updatedMap = new Map(updates.conversations.map(c => [c.id, c]));
        let changed = false;

        conversations = conversations.map(c => {
          if (updatedMap.has(c.id)) {
            changed = true;
            const updated = updatedMap.get(c.id);
            updatedMap.delete(c.id);
            return updated;
          }
          return c;
        });

        // Add new conversations not yet in the list
        if (updatedMap.size > 0) {
          conversations = [...updatedMap.values(), ...conversations];
          changed = true;
        }

        // Re-sort by last_message_at
        if (changed) {
          conversations = [...conversations].sort((a, b) =>
            new Date(b.last_message_at || 0).getTime() - new Date(a.last_message_at || 0).getTime()
          );
        }

        // Update selected conversation if it was updated
        if (selectedConversation) {
          const updatedSelected = updates.conversations.find(c => c.id === selectedConversation.id);
          if (updatedSelected) selectedConversation = updatedSelected;
        }
      }

      // Append new messages for the active conversation
      if (updates.messages?.length > 0 && selectedConversation) {
        const existingIds = new Set(messages.map(m => m.id));
        const newMsgs = updates.messages.filter(m => !existingIds.has(m.id));
        if (newMsgs.length > 0) {
          messages = [...messages, ...newMsgs];
        }
      }
    } catch {
      // Silent fail — full refresh will catch up
    }
  }

  /**
   * Refresh conversation list and active conversation messages.
   * @param {boolean} [silent] - If true, don't show loading indicator.
   */
  async function refreshConversations(silent = false) {
    if (!silent) refreshing = true;
    try {
      const params = new URLSearchParams();
      if (filters.channel) params.set('channel', filters.channel);
      if (filters.status) params.set('status', filters.status);
      if (filters.assigned_to) params.set('assigned_to', filters.assigned_to);
      if (filters.search) params.set('search', filters.search);
      const qs = params.toString();

      const freshConversations = await apiRequest(`/conversations/${qs ? '?' + qs : ''}`);
      conversations = freshConversations?.results || freshConversations || [];

      // Also refresh messages for the selected conversation
      if (selectedConversation) {
        const freshMessages = await apiRequest(`/conversations/${selectedConversation.id}/messages/`);
        messages = freshMessages?.results || freshMessages || [];

        // Update selected conversation data (e.g. status, last_message_at)
        const updated = conversations.find(c => c.id === selectedConversation.id);
        if (updated) selectedConversation = updated;
      }

      lastPollTime = new Date().toISOString();
    } catch (e) {
      if (!silent) console.error('Erro ao atualizar conversas:', e);
    } finally {
      refreshing = false;
    }
  }

  /** @param {any} conversation */
  async function selectConversation(conversation) {
    selectedConversation = conversation;
    loadingMessages = true;
    try {
      const data = await apiRequest(`/conversations/${conversation.id}/messages/`);
      messages = data.results || data || [];
    } catch (e) {
      console.error('Erro ao carregar mensagens:', e);
      toast.error('Erro ao carregar mensagens');
    } finally {
      loadingMessages = false;
    }
  }

  /** @param {string} key @param {string} value */
  function updateFilter(key, value) {
    const url = new URL($page.url);
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
    goto(url.toString(), { replaceState: true, invalidateAll: true });
  }

  function handleSearch() {
    updateFilter('search', searchQuery);
  }

  /** @param {any} newMsg */
  function onMessageSent(newMsg) {
    messages = [...messages, newMsg];
  }

  /** @param {any} contact */
  function handleConversationContactChanged(contact) {
    if (selectedConversation) {
      selectedConversation = {
        ...selectedConversation,
        contact: contact.id,
        contact_name: `${contact.first_name} ${contact.last_name}`.trim()
      };
    }
  }
</script>

<svelte:head>
  <title>Conversas - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Conversas" subtitle="Gerencie suas conversas em tempo real" />

<div class="flex h-[calc(100vh-10rem)] flex-col">
  <!-- Filters bar -->
  <div class="flex flex-wrap items-center gap-3 border-b px-4 py-3">
    <div class="relative flex-1 max-w-xs">
      <Search class="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
      <Input
        placeholder="Buscar contato..."
        class="pl-9"
        bind:value={searchQuery}
        onkeydown={(e) => e.key === 'Enter' && handleSearch()}
      />
    </div>

    <Select.Root type="single" value={filters.status || 'open'} onValueChange={(v) => updateFilter('status', v)}>
      <Select.Trigger class="w-36">
        <Filter class="size-3.5 mr-1.5 text-muted-foreground" />
        {filters.status === 'open' ? 'Abertas' : filters.status === 'pending' ? 'Pendentes' : filters.status === 'resolved' ? 'Concluídas' : 'Todas'}
      </Select.Trigger>
      <Select.Content>
        <Select.Item value="open">Abertas</Select.Item>
        <Select.Item value="pending">Pendentes</Select.Item>
        <Select.Item value="resolved">Concluídas</Select.Item>
        <Select.Item value="">Todas</Select.Item>
      </Select.Content>
    </Select.Root>

    {#if channels.length > 0}
      <Select.Root type="single" value={filters.channel || ''} onValueChange={(v) => updateFilter('channel', v)}>
        <Select.Trigger class="w-40">
          <MessageSquare class="size-3.5 mr-1.5 text-muted-foreground" />
          {channels.find(c => c.channel_type === filters.channel)?.display_name || 'Todos os canais'}
        </Select.Trigger>
        <Select.Content>
          <Select.Item value="">Todos os canais</Select.Item>
          {#each channels as ch (ch.id)}
            <Select.Item value={ch.channel_type}>{ch.display_name || ch.channel_type}</Select.Item>
          {/each}
        </Select.Content>
      </Select.Root>
    {/if}

    <div class="ml-auto flex items-center gap-2">
      <Button
        variant="ghost"
        size="icon"
        class="size-8"
        onclick={() => refreshConversations(false)}
        disabled={refreshing}
        title="Atualizar conversas"
      >
        <RefreshCw class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
      </Button>
      <Badge variant="outline" class="gap-1.5 px-3 py-1">
        <MessageSquare class="size-3.5" />
        {conversations.length} conversa{conversations.length !== 1 ? 's' : ''}
      </Badge>
    </div>
  </div>

  <!-- Main content: list + timeline -->
  <div class="flex flex-1 overflow-hidden">
    <!-- Left panel: conversation list -->
    <div class="w-80 shrink-0 overflow-y-auto border-r lg:w-96">
      <ConversationList
        {conversations}
        selected={selectedConversation?.id}
        onSelect={selectConversation}
      />
    </div>

    <!-- Right panel: timeline + input + context -->
    <div class="flex flex-1 overflow-hidden">
      <div class="flex flex-1 flex-col">
        {#if selectedConversation}
          <ConversationTimeline
            conversation={selectedConversation}
            {messages}
            loading={loadingMessages}
            onContactChanged={handleConversationContactChanged}
            onConversationChanged={(updated) => { selectedConversation = updated; }}
          >
            {#snippet headerActions()}
              <Button
                variant="ghost"
                size="icon"
                class="size-8"
                onclick={() => (showContextPanel = !showContextPanel)}
                title="Contexto do contato"
              >
                <PanelRight class="size-4" />
              </Button>
            {/snippet}
          </ConversationTimeline>
          <MessageInput
            conversationId={selectedConversation.id}
            {channels}
            currentChannel={selectedConversation.channel}
            emailSubject={selectedConversation.metadata_json?.email_subject || ''}
            {onMessageSent}
          />
        {:else}
          <div class="flex flex-1 items-center justify-center text-muted-foreground">
            <div class="text-center">
              <MessageSquare class="mx-auto mb-3 size-12 opacity-30" />
              <p class="text-sm">Selecione uma conversa para visualizar</p>
            </div>
          </div>
        {/if}
      </div>

      {#if showContextPanel && selectedConversation?.contact}
        <div class="w-72 shrink-0 overflow-y-auto border-l bg-background p-2">
          <div class="mb-2 px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Contexto do Contato
          </div>
          <RelatedEntitiesPanel
            contactId={selectedConversation.contact}
            entityType="contact"
            sections={['leads', 'opportunities', 'invoices', 'financial', 'tasks', 'cases']}
          />
        </div>
      {/if}
    </div>
  </div>
</div>
