<script>
  import { enhance } from '$app/forms';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import PageHeader from '$lib/components/layout/PageHeader.svelte';
  import { Plus, Zap, Clock, GitBranch, Share2, Eye, Trash2, Power, History } from '@lucide/svelte';

  let { data, form } = $props();

  let automations = $derived(data.automations || []);
  let filters = $derived(data.filters || {});

  // Toast on form result
  $effect(() => {
    if (form?.toast) {
      toast.success(form.toast);
    }
    if (form?.error) {
      toast.error(form.error);
    }
  });

  const typeLabels = {
    routine: 'Rotina',
    logic_rule: 'Regra Lógica',
    social: 'Social'
  };

  const typeIcons = {
    routine: Clock,
    logic_rule: GitBranch,
    social: Share2
  };

  /**
   * @param {string} type
   */
  function getTypeLabel(type) {
    return typeLabels[type] || type;
  }

  /**
   * @param {string} type
   */
  function getTypeIcon(type) {
    return typeIcons[type] || Zap;
  }

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
    goto(url.toString());
  }
</script>

<svelte:head>
  <title>Automações — TalkHub CRM</title>
</svelte:head>

<div class="flex flex-col">
  <PageHeader title="Automações" subtitle="Gerencie rotinas, regras lógicas e automações sociais.">
    {#snippet actions()}
      <Button href="/automations/new" class="gap-2">
        <Plus class="size-4" />
        <span class="hidden sm:inline">Nova Automação</span>
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
      variant={filters.type === 'routine' ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('routine')}
      class="gap-1.5"
    >
      <Clock class="size-3.5" />
      Rotinas
    </Button>
    <Button
      variant={filters.type === 'logic_rule' ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('logic_rule')}
      class="gap-1.5"
    >
      <GitBranch class="size-3.5" />
      Regras Lógicas
    </Button>
    <Button
      variant={filters.type === 'social' ? 'default' : 'outline'}
      size="sm"
      onclick={() => filterByType('social')}
      class="gap-1.5"
    >
      <Share2 class="size-3.5" />
      Social
    </Button>
  </div>

  <!-- List -->
  {#if automations.length === 0}
    <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
      <Zap class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
      <p class="text-muted-foreground text-lg font-medium">Nenhuma automação encontrada</p>
      <p class="text-muted-foreground mt-1 text-sm">Crie sua primeira automação para começar.</p>
      <Button href="/automations/new" class="mt-4 gap-2" variant="outline">
        <Plus class="size-4" />
        Nova Automação
      </Button>
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {#each automations as automation (automation.id)}
        {@const TypeIcon = getTypeIcon(automation.automation_type)}
        <div class="group rounded-lg border p-4 transition-shadow hover:shadow-md">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-2.5">
              <div class="bg-muted flex size-9 items-center justify-center rounded-lg">
                <TypeIcon class="size-5" strokeWidth={1.75} />
              </div>
              <div>
                <h3 class="text-sm font-semibold">{automation.name}</h3>
                <Badge variant="secondary" class="mt-0.5 text-[10px]">
                  {getTypeLabel(automation.automation_type)}
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
              <span>Última: {new Date(automation.last_run_at).toLocaleDateString('pt-BR')}</span>
            {/if}
          </div>

          <div class="mt-3 flex items-center gap-1.5 border-t pt-3">
            <form method="POST" action="?/toggleActive" use:enhance>
              <input type="hidden" name="id" value={automation.id} />
              <input type="hidden" name="is_active" value={automation.is_active} />
              <Button type="submit" variant="ghost" size="sm" class="h-7 gap-1 px-2 text-xs">
                <Power class="size-3" />
                {automation.is_active ? 'Desativar' : 'Ativar'}
              </Button>
            </form>
            <Button
              variant="ghost"
              size="sm"
              class="h-7 gap-1 px-2 text-xs"
              href="/automations/{automation.id}/logs"
            >
              <History class="size-3" />
              Logs
            </Button>
            <form method="POST" action="?/delete" use:enhance class="ml-auto">
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
  </div>
</div>
