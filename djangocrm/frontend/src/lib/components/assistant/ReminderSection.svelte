<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { assistant } from '$lib/api.js';
  import { formatDate } from '$lib/utils/formatting.js';
  import { Bell, BellOff, Plus, Clock, Mail, MessageSquare, Zap, Trash2, ChevronDown, ChevronRight, RotateCcw } from '@lucide/svelte';
  import AICopilot from '$lib/components/autopilot/AICopilot.svelte';

  let {
    targetType = 'financeiro.lancamento',
    targetId,
    moduleKey = 'financeiro',
    reminders = [],
    tipo = 'RECEBER',
    dateFieldLabel = 'vencimento',
    // Legacy support: lancamentoId maps to targetId
    lancamentoId,
  } = $props();

  // Backward compat: if lancamentoId provided, use it as targetId
  const resolvedTargetId = $derived(targetId || lancamentoId);
  const resolvedModuleKey = $derived(moduleKey);

  const DATE_FIELD_MAP = {
    financeiro: 'data_vencimento',
    leads: 'next_follow_up',
    opportunity: 'closed_on',
    cases: 'created_at',
    tasks: 'due_date',
    invoices: 'due_date',
  };

  const DATE_LABEL_MAP = {
    financeiro: 'vencimento',
    leads: 'follow-up',
    opportunity: 'fechamento',
    cases: 'criação (SLA)',
    tasks: 'prazo',
    invoices: 'vencimento',
  };

  const resolvedDateField = $derived(DATE_FIELD_MAP[resolvedModuleKey] || 'due_date');
  const resolvedDateLabel = $derived(dateFieldLabel || DATE_LABEL_MAP[resolvedModuleKey] || 'data');

  let policies = $state(reminders);
  let showConfig = $state(false);
  let loadingPresets = $state(false);
  let presets = $state(null);
  let saving = $state(false);
  let expanded = $state(policies.length > 0);

  // Config form state — date_field is set dynamically based on module
  let configForm = $state({
    name: '',
    trigger_type: 'due_date',
    trigger_config: { date_field: '', offsets: [-7, -3, 0, 1, 3] },
    channel_config: { channel_type: 'internal', destination_type: 'owner_email' },
    task_config: { enabled: true, mode: 'per_run', title_template: '', priority: 'High' },
    message_template: '',
    approval_policy: 'auto',
  });

  // Keep date_field in sync with module
  $effect(() => {
    if (configForm.trigger_config.date_field !== resolvedDateField) {
      configForm.trigger_config = { ...configForm.trigger_config, date_field: resolvedDateField };
    }
  });

  // Auto-load reminders when no initial data is provided (drawer pages)
  let autoLoaded = $state(false);
  $effect(() => {
    if (resolvedTargetId && reminders.length === 0 && !autoLoaded) {
      autoLoaded = true;
      assistant.getReminders(targetType, resolvedTargetId).then(result => {
        if (Array.isArray(result) && result.length > 0) {
          policies = result;
          expanded = true;
        }
      }).catch(() => {});
    }
  });

  const CHANNEL_OPTIONS = [
    { value: 'internal', label: 'Notificação interna' },
    { value: 'smtp_native', label: 'Email (SMTP)' },
  ];

  const TRIGGER_OPTIONS = [
    { value: 'due_date', label: 'Por data de vencimento' },
    { value: 'recurring', label: 'Recorrente após vencimento' },
  ];

  const OFFSET_PRESETS = [
    { label: '7d antes', value: -7 },
    { label: '5d antes', value: -5 },
    { label: '3d antes', value: -3 },
    { label: '1d antes', value: -1 },
    { label: 'No dia', value: 0 },
    { label: '1d após', value: 1 },
    { label: '3d após', value: 3 },
    { label: '7d após', value: 7 },
  ];

  function channelIcon(type) {
    if (type === 'smtp_native') return Mail;
    if (type === 'whatsapp') return MessageSquare;
    return Bell;
  }

  function triggerSummary(policy) {
    const tc = policy.trigger_config || {};
    if (policy.trigger_type === 'due_date') {
      const offsets = tc.offsets || [tc.offset_days || 0];
      return offsets.map(d => {
        if (d === 0) return 'no dia';
        if (d < 0) return `${Math.abs(d)}d antes`;
        return `${d}d após`;
      }).join(', ');
    }
    if (policy.trigger_type === 'recurring') {
      const max = tc.max_runs ? ` (max ${tc.max_runs}x)` : '';
      return `a cada ${tc.interval_days || 3} dias${max}`;
    }
    return policy.trigger_type;
  }

  async function loadPresets() {
    if (presets) return;
    loadingPresets = true;
    try {
      const result = await assistant.presets(resolvedModuleKey);
      presets = result;
    } catch {
      presets = {};
    } finally {
      loadingPresets = false;
    }
  }

  async function applyPreset(key, preset) {
    saving = true;
    try {
      const body = {
        name: preset.name,
        trigger_type: preset.trigger_type,
        trigger_config: preset.trigger_config,
        channel_config: preset.channel_config,
        task_config: preset.task_config,
        message_template: preset.message_template || '',
        approval_policy: preset.approval_policy || 'auto',
      };
      await assistant.createReminder(targetType, resolvedTargetId, body);
      await refreshPolicies();
      showConfig = false;
    } catch (err) {
      alert('Erro ao criar lembrete: ' + err.message);
    } finally {
      saving = false;
    }
  }

  async function saveCustomConfig() {
    saving = true;
    try {
      const body = {
        name: configForm.name || `Lembrete ${tipo === 'RECEBER' ? 'Receber' : 'Pagar'}`,
        trigger_type: configForm.trigger_type,
        trigger_config: configForm.trigger_config,
        channel_config: configForm.channel_config,
        task_config: configForm.task_config,
        message_template: configForm.message_template,
        approval_policy: configForm.approval_policy,
      };
      await assistant.createReminder(targetType, resolvedTargetId, body);
      await refreshPolicies();
      showConfig = false;
    } catch (err) {
      alert('Erro ao criar lembrete: ' + err.message);
    } finally {
      saving = false;
    }
  }

  async function togglePolicy(policy) {
    try {
      if (policy.is_active) {
        await assistant.deactivatePolicy(policy.id);
      } else {
        await assistant.activatePolicy(policy.id);
      }
      await refreshPolicies();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function deletePolicy(policy) {
    if (!confirm('Remover este lembrete?')) return;
    try {
      await assistant.reminderPolicies.delete(policy.id);
      await refreshPolicies();
    } catch (err) {
      alert('Erro: ' + err.message);
    }
  }

  async function refreshPolicies() {
    try {
      policies = await assistant.getReminders(targetType, resolvedTargetId);
      expanded = true;
    } catch {
      // silent
    }
  }

  let showManualConfig = $state(false);

  function handleAIGenerated(result) {
    if (result.name) configForm.name = result.name;
    if (result.trigger_type) configForm.trigger_type = result.trigger_type;
    if (result.trigger_config) configForm.trigger_config = result.trigger_config;
    if (result.channel_config) configForm.channel_config = result.channel_config;
    if (result.task_config) configForm.task_config = result.task_config;
    if (result.message_template) configForm.message_template = result.message_template;
    if (result.approval_policy) configForm.approval_policy = result.approval_policy;
    showManualConfig = true;
  }

  function toggleOffset(val) {
    const offsets = configForm.trigger_config.offsets || [];
    const idx = offsets.indexOf(val);
    if (idx >= 0) {
      configForm.trigger_config = {
        ...configForm.trigger_config,
        offsets: offsets.filter((_, i) => i !== idx),
      };
    } else {
      configForm.trigger_config = {
        ...configForm.trigger_config,
        offsets: [...offsets, val].sort((a, b) => a - b),
      };
    }
  }
</script>

<div class="rounded-lg border">
  <button
    type="button"
    class="hover:bg-muted/50 flex w-full items-center justify-between px-4 py-3 transition-colors"
    onclick={() => { expanded = !expanded; if (expanded && !presets) loadPresets(); }}
  >
    <div class="flex items-center gap-2">
      {#if expanded}
        <ChevronDown class="text-muted-foreground size-4" />
      {:else}
        <ChevronRight class="text-muted-foreground size-4" />
      {/if}
      <Bell class="size-4" />
      <span class="text-sm font-semibold">Lembretes Automáticos</span>
      {#if policies.length > 0}
        <span class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
          {policies.length} {policies.length === 1 ? 'ativo' : 'ativos'}
        </span>
      {/if}
    </div>
  </button>

  {#if expanded}
    <div class="space-y-3 border-t px-4 py-3">
      <!-- Existing policies -->
      {#if policies.length > 0}
        <div class="space-y-2">
          {#each policies as policy (policy.id)}
            {@const ChannelIcon = channelIcon(policy.channel_config?.channel_type)}
            <div class="flex items-start justify-between rounded-md border p-3 {policy.is_active ? 'bg-background' : 'bg-muted/50 opacity-60'}">
              <div class="min-w-0 flex-1 space-y-1">
                <div class="flex items-center gap-2">
                  <ChannelIcon class="size-3.5 text-muted-foreground" />
                  <span class="text-sm font-medium">{policy.name}</span>
                  {#if !policy.is_active}
                    <span class="text-xs text-muted-foreground">(pausado)</span>
                  {/if}
                </div>
                <p class="text-xs text-muted-foreground">
                  <Clock class="mr-1 inline-block size-3" />
                  {triggerSummary(policy)}
                </p>
                {#if policy.next_run_at}
                  <p class="text-xs text-muted-foreground">
                    Próximo: {formatDate(policy.next_run_at)}
                  </p>
                {/if}
                {#if policy.run_count > 0}
                  <p class="text-xs text-muted-foreground">
                    {policy.run_count} execuç{policy.run_count === 1 ? 'ão' : 'ões'}
                  </p>
                {/if}
                <!-- Upcoming jobs -->
                {#if policy.upcoming_jobs?.length > 0}
                  <div class="mt-1 space-y-0.5">
                    {#each policy.upcoming_jobs.slice(0, 3) as job}
                      <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Zap class="size-3 text-amber-500" />
                        <span>{formatDate(job.due_at)}</span>
                        <span class="rounded bg-muted px-1 py-0.5 text-[10px]">{job.status}</span>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <div class="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-7 w-7 p-0"
                  onclick={() => togglePolicy(policy)}
                  title={policy.is_active ? 'Pausar' : 'Ativar'}
                >
                  {#if policy.is_active}
                    <BellOff class="size-3.5" />
                  {:else}
                    <Bell class="size-3.5" />
                  {/if}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-7 w-7 p-0 text-destructive hover:text-destructive"
                  onclick={() => deletePolicy(policy)}
                  title="Remover"
                >
                  <Trash2 class="size-3.5" />
                </Button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

      <!-- Add reminder button / config panel -->
      {#if !showConfig}
        <Button
          variant="outline"
          size="sm"
          class="w-full"
          onclick={() => { showConfig = true; loadPresets(); }}
        >
          <Plus class="mr-1.5 size-4" /> Adicionar Lembrete
        </Button>
      {:else}
        <div class="space-y-4 rounded-md border bg-muted/30 p-4">
          <h3 class="text-sm font-semibold">Configurar Lembrete</h3>

          <!-- AI Copilot -->
          <AICopilot
            type="reminder"
            context={{ module_key: resolvedModuleKey, tipo }}
            onGenerated={handleAIGenerated}
          />

          <!-- Quick presets -->
          {#if presets && Object.keys(presets).length > 0}
            <div>
              <span class="mb-2 block text-xs font-medium text-muted-foreground">Presets Rápidos</span>
              <div class="flex flex-wrap gap-2">
                {#each Object.entries(presets) as [key, preset]}
                  <Button
                    variant="outline"
                    size="sm"
                    class="text-xs"
                    onclick={() => applyPreset(key, preset)}
                    disabled={saving}
                  >
                    <Zap class="mr-1 size-3" /> {preset.name}
                  </Button>
                {/each}
              </div>
            </div>
            <div class="relative">
              <div class="absolute inset-0 flex items-center"><span class="w-full border-t"></span></div>
              <div class="relative flex justify-center text-xs uppercase">
                <span class="bg-muted/30 px-2 text-muted-foreground">ou configure manualmente</span>
              </div>
            </div>
          {/if}

          <!-- Manual config -->
          <div class="space-y-3">
            <div>
              <label for="reminder-name" class="mb-1 block text-xs font-medium">Nome</label>
              <input
                id="reminder-name"
                type="text"
                bind:value={configForm.name}
                placeholder="Ex: Lembrete de cobrança"
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
              />
            </div>

            <div>
              <label for="trigger-type" class="mb-1 block text-xs font-medium">Tipo de Gatilho</label>
              <select
                id="trigger-type"
                bind:value={configForm.trigger_type}
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
                onchange={() => {
                  if (configForm.trigger_type === 'due_date') {
                    configForm.trigger_config = { date_field: resolvedDateField, offsets: [-3, 0, 3] };
                  } else {
                    configForm.trigger_config = { interval_days: 3, max_runs: 10, start_after: resolvedDateField };
                  }
                }}
              >
                {#each TRIGGER_OPTIONS as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>

            {#if configForm.trigger_type === 'due_date'}
              <div>
                <span class="mb-2 block text-xs font-medium">Dias relativos ao {resolvedDateLabel}</span>
                <div class="flex flex-wrap gap-1.5">
                  {#each OFFSET_PRESETS as op}
                    <button
                      type="button"
                      class="rounded-full border px-2.5 py-1 text-xs transition-colors {(configForm.trigger_config.offsets || []).includes(op.value) ? 'border-primary bg-primary text-primary-foreground' : 'border-input bg-background hover:bg-muted'}"
                      onclick={() => toggleOffset(op.value)}
                    >
                      {op.label}
                    </button>
                  {/each}
                </div>
              </div>
            {:else}
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label for="interval-days" class="mb-1 block text-xs font-medium">Intervalo (dias)</label>
                  <input
                    id="interval-days"
                    type="number"
                    min="1"
                    max="90"
                    bind:value={configForm.trigger_config.interval_days}
                    class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
                  />
                </div>
                <div>
                  <label for="max-runs" class="mb-1 block text-xs font-medium">Máximo de execuções</label>
                  <input
                    id="max-runs"
                    type="number"
                    min="1"
                    max="100"
                    bind:value={configForm.trigger_config.max_runs}
                    class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
                  />
                </div>
              </div>
            {/if}

            <div>
              <label for="channel-type" class="mb-1 block text-xs font-medium">Canal de Notificação</label>
              <select
                id="channel-type"
                bind:value={configForm.channel_config.channel_type}
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
              >
                {#each CHANNEL_OPTIONS as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>

            <div class="flex items-center gap-2">
              <input
                id="create-task"
                type="checkbox"
                bind:checked={configForm.task_config.enabled}
                class="size-4 rounded border-input"
              />
              <label for="create-task" class="text-xs font-medium">Criar tarefa automaticamente</label>
            </div>

            <div>
              <label for="msg-template" class="mb-1 block text-xs font-medium">
                Mensagem <span class="font-normal text-muted-foreground">(variáveis: &#123;&#123;contact_name&#125;&#125;, &#123;&#123;amount&#125;&#125;, &#123;&#123;due_date&#125;&#125;)</span>
              </label>
              <textarea
                id="msg-template"
                bind:value={configForm.message_template}
                rows="2"
                placeholder="Lembrete: {{contact_name}} — {{amount}} {{currency}} vence em {{due_date}}"
                class="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
              ></textarea>
            </div>

            <div>
              <label for="approval" class="mb-1 block text-xs font-medium">Aprovação</label>
              <select
                id="approval"
                bind:value={configForm.approval_policy}
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
              >
                <option value="auto">Automático</option>
                <option value="manual">Requer aprovação manual</option>
              </select>
            </div>
          </div>

          <div class="flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" onclick={() => (showConfig = false)} disabled={saving}>
              Cancelar
            </Button>
            <Button size="sm" onclick={saveCustomConfig} disabled={saving}>
              {#if saving}
                <RotateCcw class="mr-1.5 size-4 animate-spin" /> Salvando...
              {:else}
                <Plus class="mr-1.5 size-4" /> Criar Lembrete
              {/if}
            </Button>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
