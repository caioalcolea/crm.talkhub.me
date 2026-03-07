<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Plug, Settings, RefreshCw, FileText, BarChart3, AlertTriangle } from '@lucide/svelte';
  import IntegrationCard from '$lib/components/integrations/IntegrationCard.svelte';
  import IntegrationHealth from '$lib/components/integrations/IntegrationHealth.svelte';
  import { toast } from 'svelte-sonner';

  /** @type {{ data: any }} */
  let { data } = $props();

  let integrations = $derived(data.integrations || []);

  $effect(() => {
    if (data.error) toast.error(data.error);
  });
</script>

<svelte:head>
  <title>Integrações - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Hub de Integrações" subtitle="Conecte e gerencie suas integrações externas" />

<div class="mx-auto max-w-5xl space-y-6 p-6 md:p-8">
  <!-- Summary bar -->
  <div class="flex flex-wrap items-center gap-3">
    <Badge variant="outline" class="gap-1.5 px-3 py-1">
      <Plug class="size-3.5" />
      {integrations.length} integração{integrations.length !== 1 ? 'ões' : ''}
    </Badge>
    <Badge variant="outline" class="gap-1.5 px-3 py-1 border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-400">
      {integrations.filter(i => i.is_active).length} ativa{integrations.filter(i => i.is_active).length !== 1 ? 's' : ''}
    </Badge>
    <div class="flex-1"></div>
    <Button variant="outline" href="/settings/integrations/dashboard" class="gap-2">
      <BarChart3 class="size-4" />
      Dashboard
    </Button>
    <Button variant="outline" href="/settings/integrations/logs" class="gap-2">
      <FileText class="size-4" />
      Logs
    </Button>
  </div>

  <!-- Integration cards grid -->
  {#if data.error}
    <Card.Root>
      <Card.Content class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex size-16 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle class="size-8 text-destructive" />
        </div>
        <h3 class="text-lg font-semibold">Erro ao carregar integrações</h3>
        <p class="text-muted-foreground mt-1 max-w-sm text-sm">{data.error}</p>
      </Card.Content>
    </Card.Root>
  {:else if integrations.length > 0}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each integrations as integration (integration.slug)}
        <IntegrationCard {integration} />
      {/each}
    </div>
  {:else}
    <Card.Root>
      <Card.Content class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex size-16 items-center justify-center rounded-full bg-muted">
          <Plug class="size-8 text-muted-foreground" />
        </div>
        <h3 class="text-lg font-semibold">Nenhuma integração configurada</h3>
        <p class="text-muted-foreground mt-1 max-w-sm text-sm">
          As integrações disponíveis aparecerão aqui quando forem registradas pelo administrador.
        </p>
      </Card.Content>
    </Card.Root>
  {/if}
</div>
