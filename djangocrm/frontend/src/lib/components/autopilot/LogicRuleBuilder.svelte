<script>
  import { Label } from '$lib/components/ui/label/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Plus, Trash2 } from '@lucide/svelte';
  import ActionParamsForm from './ActionParamsForm.svelte';

  let { config = $bindable({}) } = $props();

  const TRIGGER_EVENTS = [
    { group: 'Leads', events: [
      { value: 'lead.created', label: 'Lead criado' },
      { value: 'lead.status_changed', label: 'Status do lead alterado' },
    ]},
    { group: 'Negócios', events: [
      { value: 'opportunity.created', label: 'Negócio criado' },
      { value: 'opportunity.stage_changed', label: 'Etapa do negócio alterada' },
    ]},
    { group: 'Chamados', events: [
      { value: 'case.created', label: 'Chamado criado' },
    ]},
    { group: 'Tarefas', events: [
      { value: 'task.completed', label: 'Tarefa concluída' },
    ]},
    { group: 'Contatos', events: [
      { value: 'contact.created', label: 'Contato criado' },
    ]},
  ];

  const OPERATORS = [
    { value: 'equals', label: 'Igual a' },
    { value: 'not_equals', label: 'Diferente de' },
    { value: 'contains', label: 'Contém' },
    { value: 'greater_than', label: 'Maior que' },
    { value: 'less_than', label: 'Menor que' },
    { value: 'is_empty', label: 'Está vazio' },
    { value: 'is_not_empty', label: 'Não está vazio' },
  ];

  const ACTION_TYPES = [
    { value: 'send_notification', label: 'Enviar Notificação' },
    { value: 'send_email', label: 'Enviar Email' },
    { value: 'create_task', label: 'Criar Tarefa' },
    { value: 'update_field', label: 'Atualizar Campo' },
  ];

  // Ensure arrays exist
  if (!Array.isArray(config.conditions)) config.conditions = [];
  if (!Array.isArray(config.actions)) config.actions = [{ action_type: '', action_params: {} }];

  function addCondition() {
    config = {
      ...config,
      conditions: [...config.conditions, { field: '', operator: 'equals', value: '' }]
    };
  }

  function removeCondition(i) {
    config = {
      ...config,
      conditions: config.conditions.filter((_, idx) => idx !== i)
    };
  }

  function addAction() {
    config = {
      ...config,
      actions: [...config.actions, { action_type: '', action_params: {} }]
    };
  }

  function removeAction(i) {
    if (config.actions.length <= 1) return;
    config = {
      ...config,
      actions: config.actions.filter((_, idx) => idx !== i)
    };
  }

  function setTrigger(val) {
    config = { ...config, trigger_event: val };
  }

  function updateCondition(i, key, val) {
    const conditions = [...config.conditions];
    conditions[i] = { ...conditions[i], [key]: val };
    config = { ...config, conditions };
  }

  function updateAction(i, key, val) {
    const actions = [...config.actions];
    actions[i] = { ...actions[i], [key]: val };
    if (key === 'action_type') actions[i].action_params = {};
    config = { ...config, actions };
  }

  function updateActionParams(i, params) {
    const actions = [...config.actions];
    actions[i] = { ...actions[i], action_params: params };
    config = { ...config, actions };
  }
</script>

<div class="space-y-5">
  <!-- Trigger -->
  <div class="space-y-2">
    <Label>Evento Gatilho</Label>
    <select
      value={config.trigger_event || ''}
      onchange={(e) => setTrigger(e.target.value)}
      class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
    >
      <option value="" disabled>Selecione o evento...</option>
      {#each TRIGGER_EVENTS as group}
        <optgroup label={group.group}>
          {#each group.events as ev}
            <option value={ev.value}>{ev.label}</option>
          {/each}
        </optgroup>
      {/each}
    </select>
  </div>

  <!-- Conditions -->
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <Label>Condições</Label>
      <Button type="button" variant="outline" size="sm" class="gap-1 text-xs h-7" onclick={addCondition}>
        <Plus class="size-3" /> Adicionar Condição
      </Button>
    </div>

    {#if config.conditions.length === 0}
      <p class="text-muted-foreground text-xs">Nenhuma condição — a ação será executada sempre que o evento ocorrer.</p>
    {/if}

    {#each config.conditions as cond, i}
      {#if i > 0}
        <div class="flex justify-center">
          <Badge variant="secondary" class="text-xs">E</Badge>
        </div>
      {/if}
      <div class="flex items-start gap-2 rounded-md border bg-muted/30 p-3">
        <div class="grid flex-1 grid-cols-3 gap-2">
          <Input
            value={cond.field}
            oninput={(e) => updateCondition(i, 'field', e.target.value)}
            placeholder="Campo (ex: status)"
            class="text-sm"
          />
          <select
            value={cond.operator}
            onchange={(e) => updateCondition(i, 'operator', e.target.value)}
            class="border-input bg-background flex h-9 rounded-md border px-2 py-1 text-sm"
          >
            {#each OPERATORS as op}
              <option value={op.value}>{op.label}</option>
            {/each}
          </select>
          {#if cond.operator !== 'is_empty' && cond.operator !== 'is_not_empty'}
            <Input
              value={cond.value}
              oninput={(e) => updateCondition(i, 'value', e.target.value)}
              placeholder="Valor"
              class="text-sm"
            />
          {:else}
            <div></div>
          {/if}
        </div>
        <Button type="button" variant="ghost" size="sm" class="text-destructive h-9 px-2" onclick={() => removeCondition(i)}>
          <Trash2 class="size-3.5" />
        </Button>
      </div>
    {/each}
  </div>

  <!-- Actions -->
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <Label>Ações</Label>
      <Button type="button" variant="outline" size="sm" class="gap-1 text-xs h-7" onclick={addAction}>
        <Plus class="size-3" /> Adicionar Ação
      </Button>
    </div>

    {#each config.actions as action, i}
      <div class="space-y-3 rounded-md border p-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-muted-foreground">Ação {i + 1}</span>
          {#if config.actions.length > 1}
            <Button type="button" variant="ghost" size="sm" class="text-destructive h-7 px-2" onclick={() => removeAction(i)}>
              <Trash2 class="size-3.5" />
            </Button>
          {/if}
        </div>
        <select
          value={action.action_type || ''}
          onchange={(e) => updateAction(i, 'action_type', e.target.value)}
          class="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm"
        >
          <option value="" disabled>Selecione a ação...</option>
          {#each ACTION_TYPES as at}
            <option value={at.value}>{at.label}</option>
          {/each}
        </select>
        {#if action.action_type}
          <ActionParamsForm
            actionType={action.action_type}
            params={action.action_params || {}}
            onchange={(p) => updateActionParams(i, p)}
          />
        {/if}
      </div>
    {/each}
  </div>
</div>
