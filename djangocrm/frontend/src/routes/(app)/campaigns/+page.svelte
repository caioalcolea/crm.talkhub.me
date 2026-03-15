<script>
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import PageHeader from '$lib/components/layout/PageHeader.svelte';
  import {
    Plus, Megaphone, Mail, MessageCircle, GitBranch,
    BarChart3, Trash2, Pause, Play, Eye
  } from '@lucide/svelte';

  let { data, form } = $props();

  let campaigns = $derived(data.campaigns || []);
  let filters = $derived(data.filters || {});

  $effect(() => {
    if (form?.toast) toast.success(form.toast);
    if (form?.error) toast.error(form.error);
  });

  const typeLabels = {
    email_blast: 'Email Blast',
    whatsapp_broadcast: 'WhatsApp',
    nurture_sequence: 'Nurture'
  };

  const typeIcons = {
    email_blast: Mail,
    whatsapp_broadcast: MessageCircle,
    nurture_sequence: GitBranch
  };

  const statusLabels = {
    draft: 'Rascunho',
    scheduled: 'Agendada',
    running: 'Em execução',
    paused: 'Pausada',
    completed: 'Concluída',
    cancelled: 'Cancelada'
  };

  const statusVariants = {
    draft: 'secondary',
    scheduled: 'outline',
    running: 'default',
    paused: 'outline',
    completed: 'secondary',
    cancelled: 'destructive'
  };

  /**
   * @param {string} type
   */
  function filterByType(type) {
    const url = new URL($page.url);
    if (type) {
      url.searchParams.set('type', type);
    } else {
      url.searchParams.delete('type');
    }
    url.searchParams.delete('status');
    goto(url.toString());
  }

  /**
   * @param {number} sent
   * @param {number} opened
   */
  function calcOpenRate(sent, opened) {
    if (!sent || sent === 0) return '0%';
    return `${Math.round((opened / sent) * 100)}%`;
  }
</script>

<svelte:head>
  <title>Campanhas — TalkHub CRM</title>
</svelte:head>

<div class="flex flex-col">
  <PageHeader title="Campanhas" subtitle="Gerencie campanhas de email, WhatsApp e nurture sequences.">
    {#snippet actions()}
      <Button href="/campaigns/new" class="gap-2">
        <Plus class="size-4" />
        <span class="hidden sm:inline">Nova Campanha</span>
        <span class="sm:hidden">Nova</span>
      </Button>
    {/snippet}
  </PageHeader>

  <div class="space-y-6 px-6 py-6 md:px-8">
  <!-- Filters -->
  <div class="flex gap-3">
    <Button
      variant={!filters.type ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('')}
    >
      Todas
    </Button>
    <Button
      variant={filters.type === 'email_blast' ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('email_blast')}
      class="gap-1.5"
    >
      <Mail class="size-3.5" />
      Email Blast
    </Button>
    <Button
      variant={filters.type === 'whatsapp_broadcast' ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('whatsapp_broadcast')}
      class="gap-1.5"
    >
      <MessageCircle class="size-3.5" />
      WhatsApp
    </Button>
    <Button
      variant={filters.type === 'nurture_sequence' ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('nurture_sequence')}
      class="gap-1.5"
    >
      <GitBranch class="size-3.5" />
      Nurture
    </Button>
  </div>

  <!-- List -->
  {#if campaigns.length === 0}
    <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
      <Megaphone class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
      <p class="text-muted-foreground text-lg font-medium">Nenhuma campanha encontrada</p>
      <p class="text-muted-foreground mt-1 text-sm">Crie sua primeira campanha para começar.</p>
      <Button href="/campaigns/new" class="mt-4 gap-2" variant="outline">
        <Plus class="size-4" />
        Nova Campanha
      </Button>
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {#each campaigns as campaign (campaign.id)}
        {@const TypeIcon = typeIcons[campaign.campaign_type] || Megaphone}
        <div class="group rounded-lg border p-4 transition-shadow hover:shadow-md">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-2.5">
              <div class="bg-muted flex size-9 items-center justify-center rounded-lg">
                <TypeIcon class="size-5" strokeWidth={1.75} />
              </div>
              <div>
                <h3 class="text-sm font-semibold">{campaign.name}</h3>
                <Badge variant="secondary" class="mt-0.5 text-[10px]">
                  {typeLabels[campaign.campaign_type] || campaign.campaign_type}
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
            <Button
              variant="ghost"
              size="sm"
              class="h-7 gap-1 px-2 text-xs"
              href="/campaigns/{campaign.id}/analytics"
            >
              <BarChart3 class="size-3" />
              Analytics
            </Button>

            {#if campaign.status === 'running'}
              <form method="POST" action="?/pauseResume" use:enhance>
                <input type="hidden" name="id" value={campaign.id} />
                <input type="hidden" name="action" value="pause" />
                <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
                  <Pause class="size-3" />
                  Pausar
                </Button>
              </form>
            {/if}

            {#if campaign.status === 'paused'}
              <form method="POST" action="?/pauseResume" use:enhance>
                <input type="hidden" name="id" value={campaign.id} />
                <input type="hidden" name="action" value="resume" />
                <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
                  <Play class="size-3" />
                  Retomar
                </Button>
              </form>
            {/if}

            {#if campaign.status === 'draft' || campaign.status === 'completed' || campaign.status === 'cancelled'}
              <form method="POST" action="?/delete" use:enhance class="ml-auto">
                <input type="hidden" name="id" value={campaign.id} />
                <Button type="submit" variant="ghost" size="sm" class="text-destructive h-7 gap-1 px-2 text-xs">
                  <Trash2 class="size-3" />
                </Button>
              </form>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
  </div>
</div>
