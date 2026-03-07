<script>
  import * as Card from '$lib/components/ui/card/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Users, MessageSquare, Clock, CheckCircle, TrendingUp, Headphones } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let flow = $derived(data.flowSummary || {});
  let agents = $derived(data.agentSummary || {});

  const widgets = $derived([
    {
      label: 'Total de Contatos',
      value: flow.total_bot_users ?? '-',
      icon: Users,
      color: 'bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400',
    },
    {
      label: 'Novos Leads Hoje',
      value: flow.day_new_bot_users ?? '-',
      icon: TrendingUp,
      color: 'bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400',
    },
    {
      label: 'Conversas Resolvidas',
      value: flow.day_done ?? '-',
      icon: CheckCircle,
      color: 'bg-green-100 dark:bg-green-950 text-green-600 dark:text-green-400',
    },
    {
      label: 'Mensagens Recebidas',
      value: flow.day_in_messages ?? '-',
      icon: MessageSquare,
      color: 'bg-violet-100 dark:bg-violet-950 text-violet-600 dark:text-violet-400',
    },
    {
      label: 'Mensagens Enviadas',
      value: flow.day_out_messages ?? '-',
      icon: MessageSquare,
      color: 'bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400',
    },
    {
      label: 'Tempo Médio de Resposta',
      value: agents.avg_agent_response_time ?? flow.avg_agent_response_time ?? '-',
      icon: Clock,
      color: 'bg-cyan-100 dark:bg-cyan-950 text-cyan-600 dark:text-cyan-400',
    },
    {
      label: 'Tempo Médio de Resolução',
      value: agents.avg_resolve_time ?? flow.avg_resolve_time ?? '-',
      icon: Headphones,
      color: 'bg-rose-100 dark:bg-rose-950 text-rose-600 dark:text-rose-400',
    },
  ]);
</script>

<svelte:head>
  <title>Analytics TalkHub Omni - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Analytics TalkHub Omni" subtitle="Métricas de conversas e atendimento" />

<div class="mx-auto max-w-4xl space-y-6 p-6 md:p-8">
  <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    {#each widgets as widget}
      <Card.Root>
        <Card.Content class="flex items-center gap-4 pt-6">
          <div class="flex size-12 shrink-0 items-center justify-center rounded-xl {widget.color}">
            <widget.icon class="size-6" />
          </div>
          <div>
            <p class="text-muted-foreground text-xs font-medium">{widget.label}</p>
            <p class="text-foreground text-2xl font-bold">{widget.value}</p>
          </div>
        </Card.Content>
      </Card.Root>
    {/each}
  </div>

  {#if agents.agents && Array.isArray(agents.agents)}
    <Card.Root>
      <Card.Header>
        <Card.Title class="text-base">Performance por Agente</Card.Title>
      </Card.Header>
      <Card.Content>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-muted-foreground border-b text-left text-xs">
                <th class="pb-2 font-medium">Agente</th>
                <th class="pb-2 font-medium">Conversas</th>
                <th class="pb-2 font-medium">Resolvidas</th>
                <th class="pb-2 font-medium">Tempo Resp.</th>
              </tr>
            </thead>
            <tbody>
              {#each agents.agents as agent}
                <tr class="border-b last:border-0">
                  <td class="py-2">{agent.name || agent.email || '-'}</td>
                  <td class="py-2">{agent.total_conversations ?? '-'}</td>
                  <td class="py-2">{agent.resolved ?? '-'}</td>
                  <td class="py-2">{agent.avg_response_time ?? '-'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </Card.Content>
    </Card.Root>
  {/if}
</div>
