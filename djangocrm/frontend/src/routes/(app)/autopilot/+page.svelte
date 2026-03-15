<script>
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { PageHeader } from '$lib/components/layout';
  import {
    Plus, Zap, Clock, GitBranch, Share2, Power, History, Trash2,
    Bell, Megaphone, Mail, MessageCircle, BarChart3, Pause, Play,
    FileCode, RefreshCw, CheckCircle, XCircle, AlertTriangle, Timer
  } from '@lucide/svelte';

  let { data, form } = $props();

  let activeTab = $derived(data.tab || 'rules');

  $effect(() => {
    if (form?.toast) toast.success(form.toast);
    if (form?.error) toast.error(form.error);
  });

  function switchTab(tab) {
    goto(`/autopilot?tab=${tab}`);
  }

  const tabs = [
    { key: 'rules', label: 'Regras', icon: Zap },
    { key: 'reminders', label: 'Lembretes', icon: Bell },
    { key: 'campaigns', label: 'Campanhas', icon: Megaphone },
    { key: 'runs', label: 'Execuções', icon: History },
    { key: 'templates', label: 'Modelos', icon: FileCode },
  ];

  // ---- Rules helpers ----
  const typeLabels = { routine: 'Rotina', logic_rule: 'Regra Lógica', social: 'Social' };
  const typeIcons = { routine: Clock, logic_rule: GitBranch, social: Share2 };

  // ---- Campaign helpers ----
  const campTypeLabels = { email_blast: 'Email Blast', whatsapp_broadcast: 'WhatsApp', nurture_sequence: 'Nurture' };
  const campTypeIcons = { email_blast: Mail, whatsapp_broadcast: MessageCircle, nurture_sequence: GitBranch };
  const statusLabels = { draft: 'Rascunho', scheduled: 'Agendada', running: 'Em execução', paused: 'Pausada', completed: 'Concluída', cancelled: 'Cancelada' };
  const statusVariants = { draft: 'secondary', scheduled: 'outline', running: 'default', paused: 'outline', completed: 'secondary', cancelled: 'destructive' };

  // ---- Reminder helpers ----
  const moduleLabels = { financeiro: 'Financeiro', leads: 'Leads', cases: 'Chamados', tasks: 'Tarefas', invoices: 'Faturas', orders: 'Pedidos', opportunity: 'Negócios' };
  const triggerLabels = { due_date: 'Data de vencimento', relative_date: 'Data relativa', recurring: 'Recorrente', cron: 'Cron', event_plus_offset: 'Evento + offset' };

  // ---- Runs helpers ----
  const jobStatusIcons = { completed: CheckCircle, failed: XCircle, pending: Timer, locked: RefreshCw, cancelled: XCircle, skipped: AlertTriangle };
  const jobStatusColors = { completed: 'text-emerald-600', failed: 'text-rose-600', pending: 'text-amber-600', locked: 'text-blue-600', cancelled: 'text-muted-foreground', skipped: 'text-muted-foreground' };

  function formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  function calcOpenRate(sent, opened) {
    if (!sent) return '0%';
    return `${Math.round((opened / sent) * 100)}%`;
  }
</script>

<svelte:head>
  <title>Autopilot — TalkHub CRM</title>
</svelte:head>

<PageHeader title="Autopilot" subtitle="Central de automações, lembretes e campanhas">
  {#snippet actions()}
    {#if activeTab === 'rules'}
      <Button href="/automations/new" class="gap-2" size="sm">
        <Plus class="size-4" /> Nova Regra
      </Button>
    {:else if activeTab === 'campaigns'}
      <Button href="/campaigns/new" class="gap-2" size="sm">
        <Plus class="size-4" /> Nova Campanha
      </Button>
    {/if}
  {/snippet}
</PageHeader>

<div class="space-y-6 p-4 md:p-6">
  <!-- Tabs -->
  <div class="flex gap-1 overflow-x-auto border-b">
    {#each tabs as tab}
      <button
        type="button"
        class="flex items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors
          {activeTab === tab.key
            ? 'border-primary text-primary'
            : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30'}"
        onclick={() => switchTab(tab.key)}
      >
        <tab.icon class="size-4" />
        {tab.label}
      </button>
    {/each}
  </div>

  <!-- Tab content: Rules -->
  {#if activeTab === 'rules'}
    {@const automations = data.automations || []}
    <!-- Type filters -->
    <div class="flex flex-wrap gap-2">
      <Button variant={!data.filters.type ? 'default' : 'outline'} size="sm" onclick={() => goto('/autopilot?tab=rules')}>Todas</Button>
      <Button variant={data.filters.type === 'routine' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=rules&type=routine')}>
        <Clock class="size-3.5" /> Rotinas
      </Button>
      <Button variant={data.filters.type === 'logic_rule' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=rules&type=logic_rule')}>
        <GitBranch class="size-3.5" /> Regras Lógicas
      </Button>
      <Button variant={data.filters.type === 'social' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=rules&type=social')}>
        <Share2 class="size-3.5" /> Social
      </Button>
    </div>

    {#if automations.length === 0}
      <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <Zap class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
        <p class="text-muted-foreground text-lg font-medium">Nenhuma automação encontrada</p>
        <Button href="/automations/new" class="mt-4 gap-2" variant="outline">
          <Plus class="size-4" /> Nova Automação
        </Button>
      </div>
    {:else}
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {#each automations as automation (automation.id)}
          {@const TypeIcon = typeIcons[automation.automation_type] || Zap}
          <div class="group rounded-lg border p-4 transition-shadow hover:shadow-md">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-2.5">
                <div class="bg-muted flex size-9 items-center justify-center rounded-lg">
                  <TypeIcon class="size-5" strokeWidth={1.75} />
                </div>
                <div>
                  <h3 class="text-sm font-semibold">{automation.name}</h3>
                  <Badge variant="secondary" class="mt-0.5 text-[10px]">
                    {typeLabels[automation.automation_type] || automation.automation_type}
                  </Badge>
                </div>
              </div>
              <Badge variant={automation.is_active ? 'default' : 'outline'} class="text-[10px]">
                {automation.is_active ? 'Ativa' : 'Inativa'}
              </Badge>
            </div>
            <div class="text-muted-foreground mt-3 flex items-center gap-4 text-xs">
              <span>{automation.run_count} execuções</span>
              {#if automation.error_count > 0}
                <span class="text-destructive">{automation.error_count} erros</span>
              {/if}
              {#if automation.last_run_at}
                <span>Última: {formatDate(automation.last_run_at)}</span>
              {/if}
            </div>
            <div class="mt-3 flex items-center gap-1.5 border-t pt-3">
              <form method="POST" action="?/toggleAutomation" use:enhance>
                <input type="hidden" name="id" value={automation.id} />
                <input type="hidden" name="is_active" value={automation.is_active} />
                <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
                  <Power class="size-3" />
                  {automation.is_active ? 'Desativar' : 'Ativar'}
                </Button>
              </form>
              <form method="POST" action="?/deleteAutomation" use:enhance class="ml-auto">
                <input type="hidden" name="id" value={automation.id} />
                <Button type="submit" variant="ghost" size="sm" class="text-destructive h-7 gap-1 px-2 text-xs">
                  <Trash2 class="size-3" />
                </Button>
              </form>
            </div>
          </div>
        {/each}
      </div>
    {/if}

  <!-- Tab content: Reminders -->
  {:else if activeTab === 'reminders'}
    {@const reminders = Array.isArray(data.reminders) ? data.reminders : (data.reminders?.results || [])}
    <!-- Module filters -->
    <div class="flex flex-wrap gap-2">
      <Button variant={!data.filters.module ? 'default' : 'outline'} size="sm" onclick={() => goto('/autopilot?tab=reminders')}>Todos</Button>
      {#each Object.entries(moduleLabels) as [key, label]}
        <Button variant={data.filters.module === key ? 'default' : 'outline'} size="sm" onclick={() => goto(`/autopilot?tab=reminders&module=${key}`)}>
          {label}
        </Button>
      {/each}
    </div>

    {#if reminders.length === 0}
      <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <Bell class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
        <p class="text-muted-foreground text-lg font-medium">Nenhum lembrete configurado</p>
        <p class="text-muted-foreground mt-1 text-sm">Lembretes são criados a partir dos lançamentos financeiros.</p>
      </div>
    {:else}
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {#each reminders as reminder (reminder.id)}
          <div class="rounded-lg border p-4 transition-shadow hover:shadow-md">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-sm font-semibold">{reminder.name}</h3>
                <div class="mt-1 flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" class="text-[10px]">{moduleLabels[reminder.module_key] || reminder.module_key}</Badge>
                  <Badge variant="outline" class="text-[10px]">{triggerLabels[reminder.trigger_type] || reminder.trigger_type}</Badge>
                </div>
              </div>
              <Badge variant={reminder.is_active ? 'default' : 'outline'} class="text-[10px]">
                {reminder.is_active ? 'Ativo' : 'Inativo'}
              </Badge>
            </div>
            <div class="text-muted-foreground mt-3 flex items-center gap-4 text-xs">
              <span>{reminder.run_count} execuções</span>
              {#if reminder.error_count > 0}
                <span class="text-destructive">{reminder.error_count} erros</span>
              {/if}
              {#if reminder.next_run_at}
                <span>Próximo: {formatDate(reminder.next_run_at)}</span>
              {/if}
            </div>
            <div class="mt-3 flex items-center gap-1.5 border-t pt-3">
              <form method="POST" action="?/toggleReminder" use:enhance>
                <input type="hidden" name="id" value={reminder.id} />
                <input type="hidden" name="is_active" value={reminder.is_active} />
                <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
                  <Power class="size-3" />
                  {reminder.is_active ? 'Desativar' : 'Ativar'}
                </Button>
              </form>
              <form method="POST" action="?/deleteReminder" use:enhance class="ml-auto">
                <input type="hidden" name="id" value={reminder.id} />
                <Button type="submit" variant="ghost" size="sm" class="text-destructive h-7 gap-1 px-2 text-xs">
                  <Trash2 class="size-3" />
                </Button>
              </form>
            </div>
          </div>
        {/each}
      </div>
    {/if}

  <!-- Tab content: Campaigns -->
  {:else if activeTab === 'campaigns'}
    {@const campaigns = data.campaigns || []}
    <!-- Type filters -->
    <div class="flex flex-wrap gap-2">
      <Button variant={!data.filters.type ? 'default' : 'outline'} size="sm" onclick={() => goto('/autopilot?tab=campaigns')}>Todas</Button>
      <Button variant={data.filters.type === 'email_blast' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=campaigns&type=email_blast')}>
        <Mail class="size-3.5" /> Email
      </Button>
      <Button variant={data.filters.type === 'whatsapp_broadcast' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=campaigns&type=whatsapp_broadcast')}>
        <MessageCircle class="size-3.5" /> WhatsApp
      </Button>
      <Button variant={data.filters.type === 'nurture_sequence' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=campaigns&type=nurture_sequence')}>
        <GitBranch class="size-3.5" /> Nurture
      </Button>
    </div>

    {#if campaigns.length === 0}
      <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <Megaphone class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
        <p class="text-muted-foreground text-lg font-medium">Nenhuma campanha encontrada</p>
        <Button href="/campaigns/new" class="mt-4 gap-2" variant="outline">
          <Plus class="size-4" /> Nova Campanha
        </Button>
      </div>
    {:else}
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {#each campaigns as campaign (campaign.id)}
          {@const TypeIcon = campTypeIcons[campaign.campaign_type] || Megaphone}
          <div class="rounded-lg border p-4 transition-shadow hover:shadow-md">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-2.5">
                <div class="bg-muted flex size-9 items-center justify-center rounded-lg">
                  <TypeIcon class="size-5" strokeWidth={1.75} />
                </div>
                <div>
                  <h3 class="text-sm font-semibold">{campaign.name}</h3>
                  <Badge variant="secondary" class="mt-0.5 text-[10px]">
                    {campTypeLabels[campaign.campaign_type] || campaign.campaign_type}
                  </Badge>
                </div>
              </div>
              <Badge variant={statusVariants[campaign.status] || 'secondary'} class="text-[10px]">
                {statusLabels[campaign.status] || campaign.status}
              </Badge>
            </div>
            <div class="text-muted-foreground mt-3 flex items-center gap-4 text-xs">
              <span>{campaign.total_recipients} destinatários</span>
              <span>{campaign.sent_count} enviados</span>
              <span>Abertura: {calcOpenRate(campaign.sent_count, campaign.opened_count)}</span>
            </div>
            <div class="mt-3 flex items-center gap-1.5 border-t pt-3">
              <Button variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs" href="/campaigns/{campaign.id}/analytics">
                <BarChart3 class="size-3" /> Analytics
              </Button>
              {#if ['running', 'completed', 'paused'].includes(campaign.status)}
                <Button variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs" onclick={() => goto(`/autopilot?tab=runs&source=campaign&campaign_id=${campaign.id}`)}>
                  <History class="size-3" /> Envios
                </Button>
              {/if}
              {#if campaign.status === 'running'}
                <form method="POST" action="?/pauseResumeCampaign" use:enhance>
                  <input type="hidden" name="id" value={campaign.id} />
                  <input type="hidden" name="action" value="pause" />
                  <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs"><Pause class="size-3" /> Pausar</Button>
                </form>
              {/if}
              {#if campaign.status === 'paused'}
                <form method="POST" action="?/pauseResumeCampaign" use:enhance>
                  <input type="hidden" name="id" value={campaign.id} />
                  <input type="hidden" name="action" value="resume" />
                  <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs"><Play class="size-3" /> Retomar</Button>
                </form>
              {/if}
              {#if ['draft', 'completed', 'cancelled'].includes(campaign.status)}
                <form method="POST" action="?/deleteCampaign" use:enhance class="ml-auto">
                  <input type="hidden" name="id" value={campaign.id} />
                  <Button type="submit" variant="ghost" size="sm" class="text-destructive h-7 gap-1 px-2 text-xs"><Trash2 class="size-3" /></Button>
                </form>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}

  <!-- Tab content: Runs -->
  {:else if activeTab === 'runs'}
    {@const runs = data.runs?.results || (Array.isArray(data.runs) ? data.runs : [])}
    <!-- Source filters -->
    <div class="flex flex-wrap gap-2">
      <Button variant={!data.filters.source ? 'default' : 'outline'} size="sm" onclick={() => goto('/autopilot?tab=runs')}>Todas</Button>
      <Button variant={data.filters.source === 'reminder' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=runs&source=reminder')}>
        <Bell class="size-3.5" /> Lembretes
      </Button>
      <Button variant={data.filters.source === 'campaign' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=runs&source=campaign')}>
        <Megaphone class="size-3.5" /> Campanhas
      </Button>
      <Button variant={data.filters.source === 'automation' ? 'default' : 'outline'} size="sm" class="gap-1.5" onclick={() => goto('/autopilot?tab=runs&source=automation')}>
        <Zap class="size-3.5" /> Automações
      </Button>
    </div>
    {#if runs.length === 0}
      <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <History class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
        <p class="text-muted-foreground text-lg font-medium">Nenhuma execução registrada</p>
        <p class="text-muted-foreground mt-1 text-sm">Execuções aparecerão aqui quando automações e lembretes forem executados.</p>
      </div>
    {:else}
      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-muted/50 border-b">
              <th class="px-3 py-2.5 text-left font-medium">Status</th>
              <th class="px-3 py-2.5 text-left font-medium">Tipo</th>
              <th class="px-3 py-2.5 text-left font-medium">Origem</th>
              <th class="hidden px-3 py-2.5 text-left font-medium sm:table-cell">Data</th>
              <th class="hidden px-3 py-2.5 text-left font-medium md:table-cell">Erro</th>
              <th class="px-3 py-2.5 text-right font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {#each runs as run (run.id)}
              {@const StatusIcon = jobStatusIcons[run.status] || Timer}
              {@const statusColor = jobStatusColors[run.status] || 'text-muted-foreground'}
              <tr class="border-b">
                <td class="px-3 py-2.5">
                  <div class="flex items-center gap-1.5">
                    <StatusIcon class="size-4 {statusColor}" />
                    <Badge variant={run.status === 'completed' ? 'secondary' : run.status === 'failed' ? 'destructive' : 'outline'} class="text-[10px]">
                      {run.status}
                    </Badge>
                  </div>
                </td>
                <td class="px-3 py-2.5 text-xs">
                  {#if run.type === 'campaign_step'}
                    <span class="flex items-center gap-1"><Megaphone class="size-3" /> Campanha</span>
                  {:else if run.type === 'reminder'}
                    <span class="flex items-center gap-1"><Bell class="size-3" /> Lembrete</span>
                  {:else if run.type === 'automation'}
                    <span class="flex items-center gap-1"><Zap class="size-3" /> Automação</span>
                  {:else}
                    {run.type || '-'}
                  {/if}
                </td>
                <td class="max-w-[200px] truncate px-3 py-2.5 text-xs">{run.name || '-'}</td>
                <td class="hidden px-3 py-2.5 text-xs sm:table-cell">{formatDate(run.executed_at || run.due_at || run.created_at)}</td>
                <td class="hidden max-w-[200px] truncate px-3 py-2.5 text-xs md:table-cell text-destructive">
                  {run.error || run.last_error || ''}
                </td>
                <td class="px-3 py-2.5 text-right">
                  {#if run.status === 'failed' || run.status === 'cancelled'}
                    <form method="POST" action="?/retryJob" use:enhance class="inline">
                      <input type="hidden" name="id" value={run.id} />
                      <Button type="submit" variant="ghost" size="sm" class="h-7 px-2 text-xs">
                        <RefreshCw class="size-3" />
                      </Button>
                    </form>
                  {/if}
                  {#if run.status === 'pending'}
                    <form method="POST" action="?/cancelJob" use:enhance class="inline">
                      <input type="hidden" name="id" value={run.id} />
                      <Button type="submit" variant="ghost" size="sm" class="text-destructive h-7 px-2 text-xs">
                        <XCircle class="size-3" />
                      </Button>
                    </form>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

  <!-- Tab content: Templates -->
  {:else if activeTab === 'templates'}
    {@const templates = Array.isArray(data.templates) ? data.templates : (data.templates?.results || [])}
    {#if templates.length === 0}
      <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <FileCode class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
        <p class="text-muted-foreground text-lg font-medium">Nenhum modelo encontrado</p>
        <p class="text-muted-foreground mt-1 text-sm">Modelos de automação e lembretes aparecerão aqui.</p>
      </div>
    {:else}
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {#each templates as template (template.id)}
          <div class="rounded-lg border p-4">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-sm font-semibold">{template.name}</h3>
                <div class="mt-1 flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" class="text-[10px]">{template.category}</Badge>
                  <Badge variant="outline" class="text-[10px]">{template.template_type}</Badge>
                  {#if template.module_key}
                    <Badge variant="outline" class="text-[10px]">{moduleLabels[template.module_key] || template.module_key}</Badge>
                  {/if}
                </div>
              </div>
              {#if template.is_system}
                <Badge variant="secondary" class="text-[10px]">Sistema</Badge>
              {/if}
            </div>
            {#if template.message_template}
              <p class="text-muted-foreground mt-3 line-clamp-2 text-xs">{template.message_template}</p>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>
