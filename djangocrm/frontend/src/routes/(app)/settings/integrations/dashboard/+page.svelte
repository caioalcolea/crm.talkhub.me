<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { BarChart3, ArrowLeft } from '@lucide/svelte';
  import MetricsWidget from '$lib/components/dashboard/MetricsWidget.svelte';
  import AgentProductivity from '$lib/components/dashboard/AgentProductivity.svelte';
  import SyncHealthPanel from '$lib/components/dashboard/SyncHealthPanel.svelte';
  import { toast } from 'svelte-sonner';

  /** @type {{ data: any }} */
  let { data } = $props();

  let metrics = $derived(data.metrics || {});
  let integrations = $derived(data.integrations || []);
  let period = $derived(data.period || '7d');

  $effect(() => {
    if (data.error) toast.error(data.error);
  });

  /** @param {string} p */
  function changePeriod(p) {
    const url = new URL($page.url);
    url.searchParams.set('period', p);
    goto(url.toString(), { replaceState: true, invalidateAll: true });
  }
</script>

<svelte:head>
  <title>Dashboard de Integrações - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Dashboard de Integrações" subtitle="Métricas e saúde das integrações" />

<div class="mx-auto max-w-5xl space-y-6 p-6 md:p-8">
  <!-- Top bar -->
  <div class="flex items-center justify-between">
    <Button variant="ghost" size="sm" class="gap-1.5" href="/settings/integrations">
      <ArrowLeft class="size-4" />
      Voltar
    </Button>

    <Select.Root type="single" value={period} onValueChange={changePeriod}>
      <Select.Trigger class="w-36">
        <BarChart3 class="size-3.5 mr-1.5 text-muted-foreground" />
        {period === '1d' ? 'Hoje' : period === '7d' ? '7 dias' : period === '30d' ? '30 dias' : 'Personalizado'}
      </Select.Trigger>
      <Select.Content>
        <Select.Item value="1d">Hoje</Select.Item>
        <Select.Item value="7d">7 dias</Select.Item>
        <Select.Item value="30d">30 dias</Select.Item>
      </Select.Content>
    </Select.Root>
  </div>

  <!-- Metrics grid -->
  <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <MetricsWidget title="Usuários de Bot" value={metrics.bot_users ?? 0} icon="bot" />
    <MetricsWidget title="Mensagens" value={metrics.messages_count ?? 0} icon="message" change={metrics.messages_change} />
    <MetricsWidget title="Tempo Médio Resposta" value={metrics.avg_response_time ?? '—'} icon="clock" suffix="min" />
    <MetricsWidget title="Taxa de Resolução" value={metrics.resolution_rate ?? 0} icon="check" suffix="%" />
  </div>

  <!-- Agent productivity + Sync health -->
  <div class="grid gap-6 lg:grid-cols-2">
    <AgentProductivity agents={metrics.top_agents || []} />
    <SyncHealthPanel {integrations} />
  </div>
</div>
