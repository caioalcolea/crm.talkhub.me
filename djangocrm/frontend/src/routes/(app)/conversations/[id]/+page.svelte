<script>
  import { goto } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { PageHeader } from '$lib/components/layout';
  import ConversationTimeline from '$lib/components/conversations/ConversationTimeline.svelte';
  import MessageInput from '$lib/components/conversations/MessageInput.svelte';
  import { ArrowLeft, PanelRight } from '@lucide/svelte';
  import { RelatedEntitiesPanel } from '$lib/components/ui/related-entities/index.js';
  import { toast } from 'svelte-sonner';

  /** @type {{ data: any }} */
  let { data } = $props();

  let conversationData = $derived(data.conversation);
  let initialMessages = $derived(data.messages || []);
  /** @type {any} */
  let conversation = $state(null);
  let messages = $state([]);
  let channels = $derived(data.channels || []);
  let showContextPanel = $state(false);

  $effect(() => {
    conversation = conversationData;
  });

  $effect(() => {
    messages = initialMessages;
  });

  $effect(() => {
    if (data.error) toast.error(data.error);
  });

  /** @param {any} msg */
  function onMessageSent(msg) {
    messages = [...messages, msg];
  }

  /** @param {any} contact */
  function handleConversationContactChanged(contact) {
    if (conversation) {
      conversation = {
        ...conversation,
        contact: contact.id,
        contact_name: `${contact.first_name} ${contact.last_name}`.trim()
      };
    }
  }
</script>

<svelte:head>
  <title>{conversation?.contact_name || 'Conversa'} - TalkHub CRM</title>
</svelte:head>

<div class="flex h-[calc(100vh-4rem)] flex-col">
  <!-- Top bar -->
  <div class="flex items-center gap-3 border-b px-4 py-2">
    <Button variant="ghost" size="icon" class="size-8" onclick={() => goto('/conversations')}>
      <ArrowLeft class="size-4" />
    </Button>
    <span class="text-sm font-medium">{conversation?.contact_name || 'Conversa'}</span>
  </div>

  {#if data.error}
    <div class="flex flex-1 items-center justify-center text-muted-foreground">
      <div class="text-center">
        <p class="text-destructive font-medium text-sm">Erro ao carregar conversa</p>
        <p class="text-muted-foreground mt-1 text-xs">{data.error}</p>
      </div>
    </div>
  {:else if conversation}
    <div class="flex flex-1 overflow-hidden">
      <div class="flex flex-1 flex-col">
        <ConversationTimeline
          {conversation}
          {messages}
          onContactChanged={handleConversationContactChanged}
          onConversationChanged={(updated) => { conversation = updated; }}
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
          conversationId={conversation.id}
          {channels}
          currentChannel={conversation.channel}
          emailSubject={conversation.metadata_json?.email_subject || ''}
          {onMessageSent}
        />
      </div>

      {#if showContextPanel && conversation?.contact}
        <div class="w-72 shrink-0 overflow-y-auto border-l bg-background p-2">
          <div class="mb-2 px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Contexto do Contato
          </div>
          <RelatedEntitiesPanel
            contactId={conversation.contact}
            entityType="contact"
            sections={['leads', 'opportunities', 'invoices', 'financial', 'tasks', 'cases']}
          />
        </div>
      {/if}
    </div>
  {:else}
    <div class="flex flex-1 items-center justify-center text-muted-foreground">
      <p class="text-sm">Conversa não encontrada</p>
    </div>
  {/if}
</div>
