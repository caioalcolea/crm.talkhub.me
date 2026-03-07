<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { Trophy, TrendingUp, AlertTriangle, Clock, CheckCircle2, Users, ChevronDown, ChevronRight, ArrowLeft } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Progress } from '$lib/components/ui/progress/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';
  import { getStatusColor, getProgressColor } from '$lib/utils/goals.js';

  const periodTypeOptions = [
    { value: '', label: 'Todos os Períodos' },
    { value: 'MONTHLY', label: 'Mensal' },
    { value: 'QUARTERLY', label: 'Trimestral' },
    { value: 'YEARLY', label: 'Anual' },
    { value: 'CUSTOM', label: 'Personalizado' }
  ];

  const breakdownTypeLabels = {
    user: 'Usuário',
    product: 'Produto',
    channel: 'Canal',
    stage: 'Estágio'
  };

  const statusLabels = {
    on_track: 'No Caminho',
    at_risk: 'Em Risco',
    behind: 'Atrasado',
    completed: 'Concluído'
  };

  /** @type {{ data: any }} */
  let { data } = $props();

  const orgCurrency = $derived($orgSettings.default_currency || 'BRL');

  // Filter state
  let selectedPeriod = $state(data.filters?.periodType || '');
  let selectedTeam = $state(data.filters?.teamId || '');

  // Expanded goals (for showing breakdowns)
  /** @type {Set<string>} */
  let expandedGoals = $state(new Set());

  /**
   * Toggle breakdown visibility for a goal
   * @param {string} goalId
   */
  const toggleBreakdowns = (goalId) => {
    const next = new Set(expandedGoals);
    if (next.has(goalId)) {
      next.delete(goalId);
    } else {
      next.add(goalId);
    }
    expandedGoals = next;
  };

  /**
   * Apply filters via URL params
   */
  const applyFilters = () => {
    const params = new URLSearchParams();
    if (selectedPeriod) params.set('period_type', selectedPeriod);
    if (selectedTeam) params.set('team', selectedTeam);
    const qs = params.toString();
    goto(`/goals/dashboard${qs ? `?${qs}` : ''}`, { invalidateAll: true });
  };

  /**
   * Format value based on goal type
   * @param {number} value
   * @param {string} goalType
   */
  const formatGoalValue = (value, goalType) => {
    if (goalType === 'REVENUE') {
      return formatCurrency(value, orgCurrency);
    }
    return value.toLocaleString('pt-BR');
  };

  /**
   * Get status icon component
   * @param {string} statusValue
   */
  const getStatusIcon = (statusValue) => {
    switch (statusValue) {
      case 'on_track': return TrendingUp;
      case 'at_risk': return AlertTriangle;
      case 'behind': return Clock;
      case 'completed': return CheckCircle2;
      default: return Clock;
    }
  };

  /**
   * Get status badge classes
   * @param {string} statusValue
   */
  const getStatusBadge = (statusValue) => {
    switch (statusValue) {
      case 'on_track':
        return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400';
      case 'at_risk':
        return 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400';
      case 'behind':
        return 'bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-400';
      case 'completed':
        return 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400';
      default:
        return 'bg-gray-50 text-gray-700 dark:bg-gray-500/15 dark:text-gray-400';
    }
  };
</script>

<div class="mx-auto max-w-7xl space-y-6 p-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="icon" onclick={() => goto('/goals')}>
        <ArrowLeft class="size-5" />
      </Button>
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Dashboard de Metas</h1>
        <p class="text-muted-foreground text-sm">Visão consolidada do progresso das metas ativas</p>
      </div>
    </div>
  </div>

  <!-- Summary Cards -->
  <div class="grid grid-cols-2 gap-4 md:grid-cols-5">
    <Card.Root>
      <Card.Content class="flex items-center gap-3 p-4">
        <div class="rounded-lg bg-blue-50 p-2 dark:bg-blue-500/15">
          <Trophy class="size-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p class="text-muted-foreground text-xs font-medium">Total</p>
          <p class="text-2xl font-bold">{data.summary.total_goals}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-3 p-4">
        <div class="rounded-lg bg-emerald-50 p-2 dark:bg-emerald-500/15">
          <TrendingUp class="size-5 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <p class="text-muted-foreground text-xs font-medium">No Caminho</p>
          <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{data.summary.on_track}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-3 p-4">
        <div class="rounded-lg bg-amber-50 p-2 dark:bg-amber-500/15">
          <AlertTriangle class="size-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <p class="text-muted-foreground text-xs font-medium">Em Risco</p>
          <p class="text-2xl font-bold text-amber-600 dark:text-amber-400">{data.summary.at_risk}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-3 p-4">
        <div class="rounded-lg bg-red-50 p-2 dark:bg-red-500/15">
          <Clock class="size-5 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <p class="text-muted-foreground text-xs font-medium">Atrasado</p>
          <p class="text-2xl font-bold text-red-600 dark:text-red-400">{data.summary.behind}</p>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Content class="flex items-center gap-3 p-4">
        <div class="rounded-lg bg-blue-50 p-2 dark:bg-blue-500/15">
          <CheckCircle2 class="size-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p class="text-muted-foreground text-xs font-medium">Concluído</p>
          <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">{data.summary.completed}</p>
        </div>
      </Card.Content>
    </Card.Root>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-3">
    <Select.Root type="single" value={selectedPeriod} onValueChange={(v) => { selectedPeriod = v ?? ''; }}>
      <Select.Trigger class="w-[180px]">
        {periodTypeOptions.find((o) => o.value === selectedPeriod)?.label || 'Todos os Períodos'}
      </Select.Trigger>
      <Select.Content>
        {#each periodTypeOptions as option (option.value)}
          <Select.Item value={option.value}>{option.label}</Select.Item>
        {/each}
      </Select.Content>
    </Select.Root>

    {#if data.options.teams.length > 0}
      <Select.Root type="single" value={selectedTeam} onValueChange={(v) => { selectedTeam = v ?? ''; }}>
        <Select.Trigger class="w-[180px]">
          {data.options.teams.find((t) => t.id === selectedTeam)?.name || 'Todas as Equipes'}
        </Select.Trigger>
        <Select.Content>
          <Select.Item value="">Todas as Equipes</Select.Item>
          {#each data.options.teams as team (team.id)}
            <Select.Item value={team.id}>{team.name}</Select.Item>
          {/each}
        </Select.Content>
      </Select.Root>
    {/if}

    <Button variant="outline" size="sm" onclick={applyFilters}>
      Filtrar
    </Button>
  </div>
</div>

<!-- Goals List with Breakdowns (continued from above, inside the same root div) -->
<div class="mx-auto max-w-7xl space-y-4 px-6 pb-6">
  {#if data.goals.length === 0}
    <Card.Root>
      <Card.Content class="flex flex-col items-center justify-center py-12">
        <Trophy class="text-muted-foreground/40 mb-3 size-12" />
        <p class="text-muted-foreground text-sm">Nenhuma meta ativa encontrada para o período selecionado.</p>
        <Button variant="outline" size="sm" class="mt-4" onclick={() => goto('/goals')}>
          Gerenciar Metas
        </Button>
      </Card.Content>
    </Card.Root>
  {:else}
    {#each data.goals as goal (goal.id)}
      <Card.Root class="overflow-hidden transition-shadow hover:shadow-md">
        <Card.Content class="p-0">
          <!-- Goal Header -->
          <div class="flex items-center gap-4 p-5">
            <!-- Expand toggle (only if has breakdowns) -->
            <button
              class="flex size-8 shrink-0 items-center justify-center rounded-md transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 {goal.breakdowns.length === 0 ? 'invisible' : ''}"
              onclick={() => toggleBreakdowns(goal.id)}
              aria-label="Expandir desdobramentos"
            >
              {#if expandedGoals.has(goal.id)}
                <ChevronDown class="size-4" />
              {:else}
                <ChevronRight class="size-4" />
              {/if}
            </button>

            <!-- Goal Info -->
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <h3 class="truncate text-sm font-semibold">{goal.name}</h3>
                <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium {getStatusBadge(goal.status)}">
                  <svelte:component this={getStatusIcon(goal.status)} class="size-3" />
                  {statusLabels[goal.status] || goal.status}
                </span>
              </div>
              <div class="text-muted-foreground mt-0.5 flex items-center gap-3 text-xs">
                <span>{goal.goalType === 'REVENUE' ? 'Receita' : 'Negócios'}</span>
                <span>·</span>
                {#if goal.assignedTo}
                  <span class="flex items-center gap-1">
                    <Users class="size-3" />
                    {goal.assignedTo.name}
                  </span>
                {:else if goal.team}
                  <span class="flex items-center gap-1">
                    <Users class="size-3" />
                    {goal.team.name}
                  </span>
                {/if}
                <span>·</span>
                <span>{goal.daysRemaining} dias restantes</span>
              </div>
            </div>

            <!-- Progress -->
            <div class="flex shrink-0 items-center gap-4">
              <div class="text-right">
                <p class="text-sm font-semibold {getStatusColor(goal.status)}">
                  {formatGoalValue(goal.progressValue, goal.goalType)}
                </p>
                <p class="text-muted-foreground text-xs">
                  de {formatGoalValue(goal.targetValue, goal.goalType)}
                </p>
              </div>
              <div class="w-32">
                <Progress value={goal.progressPercent} max={100} class="h-2 {getProgressColor(goal.progressPercent)}" />
                <p class="text-muted-foreground mt-1 text-right text-[10px] font-medium">{goal.progressPercent}%</p>
              </div>
            </div>
          </div>

          <!-- Breakdowns Table (expandable) -->
          {#if expandedGoals.has(goal.id) && goal.breakdowns.length > 0}
            <div class="border-t bg-gray-50/50 dark:bg-gray-900/30">
              <div class="px-5 py-3">
                <p class="text-muted-foreground mb-2 text-xs font-semibold uppercase tracking-wider">
                  Desdobramentos
                </p>
                <div class="space-y-2">
                  {#each goal.breakdowns as bd (bd.id)}
                    <div class="flex items-center gap-3 rounded-lg bg-white p-3 shadow-sm dark:bg-gray-800/50">
                      <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                          <span class="text-muted-foreground rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium dark:bg-gray-700">
                            {breakdownTypeLabels[bd.breakdownType] || bd.breakdownType}
                          </span>
                          <span class="truncate text-sm font-medium">{bd.breakdownLabel}</span>
                        </div>
                      </div>
                      <div class="flex shrink-0 items-center gap-3">
                        <span class="text-xs {getStatusColor(bd.status)}">
                          {formatGoalValue(bd.currentValue, goal.goalType)} / {formatGoalValue(bd.targetValue, goal.goalType)}
                        </span>
                        <div class="w-20">
                          <Progress value={bd.progressPercent} max={100} class="h-1.5 {getProgressColor(bd.progressPercent)}" />
                        </div>
                        <span class="w-10 text-right text-[10px] font-medium {getStatusColor(bd.status)}">
                          {bd.progressPercent}%
                        </span>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          {/if}
        </Card.Content>
      </Card.Root>
    {/each}
  {/if}
</div>
