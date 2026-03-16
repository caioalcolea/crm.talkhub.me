<script>
  import { enhance } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import CampaignAnalytics from './CampaignAnalytics.svelte';
  import {
    Users, Calendar, Search, Megaphone, ArrowLeft,
    BarChart3, Pause, Play, ChevronDown, ChevronUp
  } from '@lucide/svelte';

  let { campaign, onBack = () => {}, form = null } = $props();

  // Audience builder state
  let filterTags = $state('');
  let filterSource = $state('');
  let filterCity = $state('');
  let filterState = $state('');
  let filterHasEmail = $state(false);
  let filterHasPhone = $state(false);
  let filterIsActive = $state(true);
  let audienceName = $state('Audiência Principal');
  let previewCount = $state(-1);

  // Schedule state
  let scheduledAt = $state('');

  // Analytics toggle
  let showAnalytics = $state(false);

  $effect(() => {
    if (form?.toast) {
      toast.success(form.toast);
      invalidateAll();
    }
    if (form?.error) toast.error(form.error);
    if (form?.previewCount !== undefined) previewCount = form.previewCount;
  });

  let filterCriteria = $derived(() => {
    const criteria = {};
    if (filterTags.trim()) criteria.tags = filterTags.split(',').map((t) => t.trim()).filter(Boolean);
    if (filterSource.trim()) criteria.source = filterSource.trim();
    if (filterCity.trim()) criteria.city = filterCity.trim();
    if (filterState.trim()) criteria.state = filterState.trim();
    if (filterHasEmail) criteria.has_email = true;
    if (filterHasPhone) criteria.has_phone = true;
    if (filterIsActive) criteria.is_active = true;
    return criteria;
  });

  let filterCriteriaJson = $derived(JSON.stringify(filterCriteria()));

  const statusLabels = {
    draft: 'Rascunho', scheduled: 'Agendada', running: 'Em execução',
    paused: 'Pausada', completed: 'Concluída', cancelled: 'Cancelada'
  };
  const statusVariants = {
    draft: 'secondary', scheduled: 'outline', running: 'default',
    paused: 'outline', completed: 'secondary', cancelled: 'destructive'
  };
</script>

<div class="space-y-5">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="sm" class="gap-1.5" onclick={onBack}>
        <ArrowLeft class="size-4" />
        Voltar
      </Button>
      <div>
        <h2 class="text-lg font-semibold">{campaign.name || 'Campanha'}</h2>
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <span>{campaign.campaign_type || ''}</span>
          <Badge variant={statusVariants[campaign.status] || 'secondary'} class="text-[10px]">
            {statusLabels[campaign.status] || campaign.status}
          </Badge>
          <span>{campaign.total_recipients || 0} destinatários</span>
        </div>
      </div>
    </div>
    <div class="flex items-center gap-2">
      {#if campaign.status === 'running'}
        <form method="POST" action="?/pauseResumeCampaign" use:enhance>
          <input type="hidden" name="id" value={campaign.id} />
          <input type="hidden" name="action" value="pause" />
          <Button type="submit" variant="outline" size="sm" class="gap-1.5">
            <Pause class="size-3.5" /> Pausar
          </Button>
        </form>
      {/if}
      {#if campaign.status === 'paused'}
        <form method="POST" action="?/pauseResumeCampaign" use:enhance>
          <input type="hidden" name="id" value={campaign.id} />
          <input type="hidden" name="action" value="resume" />
          <Button type="submit" size="sm" class="gap-1.5">
            <Play class="size-3.5" /> Retomar
          </Button>
        </form>
      {/if}
    </div>
  </div>

  <!-- Audience Builder (only for draft/scheduled) -->
  {#if campaign.status === 'draft' || campaign.status === 'scheduled'}
    <div class="rounded-lg border p-5 space-y-4">
      <div class="flex items-center gap-2">
        <Users class="size-5" />
        <h3 class="text-base font-semibold">Construtor de Audiência</h3>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div class="space-y-1">
          <Label>Tags (separadas por vírgula)</Label>
          <Input bind:value={filterTags} placeholder="vip, cliente-ativo" />
        </div>
        <div class="space-y-1">
          <Label>Fonte</Label>
          <Input bind:value={filterSource} placeholder="Ex: website, indicação" />
        </div>
        <div class="space-y-1">
          <Label>Cidade</Label>
          <Input bind:value={filterCity} placeholder="São Paulo" />
        </div>
        <div class="space-y-1">
          <Label>Estado</Label>
          <Input bind:value={filterState} placeholder="SP" />
        </div>
        <div class="flex items-end gap-4">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" bind:checked={filterHasEmail} class="rounded" />
            Tem email
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" bind:checked={filterHasPhone} class="rounded" />
            Tem telefone
          </label>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" bind:checked={filterIsActive} class="rounded" />
            Apenas ativos
          </label>
        </div>
      </div>

      <div class="flex items-center gap-3 pt-2">
        <form method="POST" action="?/previewAudience" use:enhance>
          <input type="hidden" name="campaign_id" value={campaign.id} />
          <input type="hidden" name="filter_criteria" value={filterCriteriaJson} />
          <Button type="submit" variant="outline" size="sm" class="gap-1.5">
            <Search class="size-3.5" /> Preview
          </Button>
        </form>
        {#if previewCount >= 0}
          <span class="text-sm font-medium">{previewCount} contatos encontrados</span>
        {/if}
      </div>

      {#if previewCount > 0}
        <form method="POST" action="?/generateAudience" use:enhance class="flex items-end gap-3 border-t pt-4">
          <input type="hidden" name="campaign_id" value={campaign.id} />
          <input type="hidden" name="filter_criteria" value={filterCriteriaJson} />
          <div class="flex-1 space-y-1">
            <Label>Nome da Audiência</Label>
            <Input name="audience_name" bind:value={audienceName} />
          </div>
          <Button type="submit" size="sm" class="gap-1.5">
            <Users class="size-3.5" /> Gerar Destinatários
          </Button>
        </form>
      {/if}
    </div>
  {/if}

  <!-- Schedule (only for draft with recipients) -->
  {#if campaign.status === 'draft' && campaign.total_recipients > 0}
    <div class="rounded-lg border p-5 space-y-4">
      <div class="flex items-center gap-2">
        <Calendar class="size-5" />
        <h3 class="text-base font-semibold">Agendar Envio</h3>
      </div>

      <div class="bg-muted/50 rounded-md p-3 text-sm space-y-1">
        <p><span class="font-medium">Tipo:</span> {campaign.campaign_type}</p>
        <p><span class="font-medium">Destinatários:</span> {campaign.total_recipients}</p>
        {#if campaign.subject}
          <p><span class="font-medium">Assunto:</span> {campaign.subject}</p>
        {/if}
      </div>

      <form method="POST" action="?/scheduleCampaign" use:enhance class="flex items-end gap-3">
        <input type="hidden" name="campaign_id" value={campaign.id} />
        <div class="flex-1 space-y-1">
          <Label for="scheduled-at">Data e Hora</Label>
          <Input id="scheduled-at" name="scheduled_at" type="datetime-local" bind:value={scheduledAt} required />
        </div>
        <Button type="submit" size="sm" class="gap-1.5" disabled={!scheduledAt}>
          <Megaphone class="size-3.5" /> Agendar Campanha
        </Button>
      </form>
    </div>
  {/if}

  <!-- Campaign Info (for non-draft) -->
  {#if campaign.status !== 'draft'}
    <div class="rounded-lg border p-5 space-y-3">
      <h3 class="text-base font-semibold">Informações</h3>
      <div class="grid gap-2 text-sm sm:grid-cols-2">
        <p><span class="text-muted-foreground">Tipo:</span> {campaign.campaign_type}</p>
        <p><span class="text-muted-foreground">Destinatários:</span> {campaign.total_recipients}</p>
        <p><span class="text-muted-foreground">Enviados:</span> {campaign.sent_count}</p>
        <p><span class="text-muted-foreground">Abertos:</span> {campaign.opened_count}</p>
        {#if campaign.scheduled_at}
          <p><span class="text-muted-foreground">Agendada para:</span> {new Date(campaign.scheduled_at).toLocaleString('pt-BR')}</p>
        {/if}
        {#if campaign.started_at}
          <p><span class="text-muted-foreground">Iniciada em:</span> {new Date(campaign.started_at).toLocaleString('pt-BR')}</p>
        {/if}
        {#if campaign.completed_at}
          <p><span class="text-muted-foreground">Concluída em:</span> {new Date(campaign.completed_at).toLocaleString('pt-BR')}</p>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Analytics expandable section -->
  <div class="rounded-lg border">
    <button
      type="button"
      class="flex w-full items-center justify-between p-4 hover:bg-muted/30 transition-colors"
      onclick={() => showAnalytics = !showAnalytics}
    >
      <div class="flex items-center gap-2">
        <BarChart3 class="size-5" />
        <span class="font-semibold">Analytics</span>
      </div>
      {#if showAnalytics}
        <ChevronUp class="size-4 text-muted-foreground" />
      {:else}
        <ChevronDown class="size-4 text-muted-foreground" />
      {/if}
    </button>
    {#if showAnalytics}
      <div class="border-t px-4 pb-4 pt-3">
        <CampaignAnalytics campaignId={campaign.id} />
      </div>
    {/if}
  </div>
</div>
