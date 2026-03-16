<script>
  import { Label } from '$lib/components/ui/label/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Plus, Trash2 } from '@lucide/svelte';
  import ActionParamsForm from './ActionParamsForm.svelte';

  let { config = $bindable({}) } = $props();

  const CHANNELS = [
    { value: 'whatsapp', label: 'WhatsApp' },
    { value: 'instagram', label: 'Instagram' },
    { value: 'facebook', label: 'Facebook' },
    { value: 'telegram', label: 'Telegram' },
  ];

  const EVENTS = [
    { value: 'message_received', label: 'Mensagem recebida' },
    { value: 'message_read', label: 'Mensagem lida' },
    { value: 'contact_started', label: 'Contato iniciado' },
    { value: 'contact_opted_out', label: 'Contato optou por sair' },
  ];

  const ACTION_TYPES = [
    { value: 'auto_reply', label: 'Resposta Automática' },
    { value: 'assign_to_user', label: 'Atribuir a Usuário' },
    { value: 'create_lead', label: 'Criar Lead' },
    { value: 'add_tag', label: 'Adicionar Tag' },
    { value: 'send_to_automation_router', label: 'Enviar ao Router' },
  ];

  if (!Array.isArray(config.actions)) config.actions = [{ action_type: '', action_params: {} }];

  function setChannel(ch) {
    config = { ...config, channel_type: ch };
  }

  function setEvent(ev) {
    config = { ...config, social_event: ev };
  }

  function addAction() {
    config = { ...config, actions: [...config.actions, { action_type: '', action_params: {} }] };
  }

  function removeAction(i) {
    if (config.actions.length <= 1) return;
    config = { ...config, actions: config.actions.filter((_, idx) => idx !== i) };
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
  <!-- Channel -->
  <div class="space-y-2">
    <Label>Canal</Label>
    <div class="flex gap-1">
      {#each CHANNELS as ch}
        <Button
          type="button"
          variant={config.channel_type === ch.value ? 'default' : 'outline'}
          size="sm"
          onclick={() => setChannel(ch.value)}
        >{ch.label}</Button>
      {/each}
    </div>
  </div>

  <!-- Event -->
  <div class="space-y-2">
    <Label>Evento</Label>
    <select
      value={config.social_event || ''}
      onchange={(e) => setEvent(e.target.value)}
      class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
    >
      <option value="" disabled>Selecione o evento...</option>
      {#each EVENTS as ev}
        <option value={ev.value}>{ev.label}</option>
      {/each}
    </select>
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
