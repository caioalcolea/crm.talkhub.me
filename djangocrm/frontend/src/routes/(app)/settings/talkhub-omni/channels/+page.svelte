<script>
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Radio, Bot } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let channelsList = $derived(() => {
    const raw = data.channels;
    if (Array.isArray(raw)) return raw;
    if (raw?.channels && Array.isArray(raw.channels)) return raw.channels;
    if (raw?.data && Array.isArray(raw.data)) return raw.data;
    return [];
  });

  let flowsList = $derived(() => {
    const raw = data.flows;
    if (Array.isArray(raw)) return raw;
    if (raw?.flows && Array.isArray(raw.flows)) return raw.flows;
    if (raw?.data && Array.isArray(raw.data)) return raw.data;
    return [];
  });
</script>

<svelte:head>
  <title>Canais TalkHub Omni - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Canais & Fluxos" subtitle="Canais ativos e bots do TalkHub Omni" />

<div class="mx-auto max-w-4xl space-y-6 p-6 md:p-8">
  <!-- Channels -->
  <Card.Root>
    <Card.Header>
      <div class="flex items-center gap-3">
        <Radio class="size-5 text-violet-600 dark:text-violet-400" />
        <Card.Title>Canais Ativos</Card.Title>
      </div>
    </Card.Header>
    <Card.Content>
      {#if channelsList().length === 0}
        <p class="text-muted-foreground py-4 text-center text-sm">Nenhum canal encontrado.</p>
      {:else}
        <div class="grid gap-3 sm:grid-cols-2">
          {#each channelsList() as channel}
            <div class="bg-muted/50 flex items-center gap-3 rounded-lg p-3">
              <div class="flex size-9 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-950">
                <Radio class="size-4 text-violet-600 dark:text-violet-400" />
              </div>
              <div class="flex-1">
                <p class="text-foreground text-sm font-medium">{channel.name || channel.type || 'Canal'}</p>
                {#if channel.type}
                  <p class="text-muted-foreground text-xs capitalize">{channel.type}</p>
                {/if}
              </div>
              {#if channel.status === 'active' || channel.is_active}
                <Badge class="border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">Ativo</Badge>
              {:else}
                <Badge variant="outline">Inativo</Badge>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </Card.Content>
  </Card.Root>

  <!-- Flows/Bots -->
  <Card.Root>
    <Card.Header>
      <div class="flex items-center gap-3">
        <Bot class="size-5 text-violet-600 dark:text-violet-400" />
        <Card.Title>Fluxos & Bots</Card.Title>
      </div>
    </Card.Header>
    <Card.Content>
      {#if flowsList().length === 0}
        <p class="text-muted-foreground py-4 text-center text-sm">Nenhum fluxo encontrado.</p>
      {:else}
        <div class="space-y-2">
          {#each flowsList() as flow}
            <div class="bg-muted/50 flex items-center justify-between rounded-lg p-3">
              <div>
                <p class="text-foreground text-sm font-medium">{flow.name || flow.title || 'Fluxo'}</p>
                {#if flow.description}
                  <p class="text-muted-foreground text-xs">{flow.description}</p>
                {/if}
              </div>
              {#if flow.status === 'active' || flow.is_active}
                <Badge class="border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">Ativo</Badge>
              {:else}
                <Badge variant="outline">{flow.status || 'Inativo'}</Badge>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </Card.Content>
  </Card.Root>
</div>
