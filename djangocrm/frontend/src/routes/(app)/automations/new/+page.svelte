<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { ArrowLeft, Zap } from '@lucide/svelte';

  let { form } = $props();

  let name = $state('');
  let automationType = $state('');
  let configJson = $state('{}');

  $effect(() => {
    if (form?.error) {
      toast.error(form.error);
    }
  });

  // Template configs por tipo
  const configTemplates = {
    routine: JSON.stringify({
      schedule_cron: 60,
      action_type: 'send_notification',
      action_params: { message: 'Rotina executada' }
    }, null, 2),
    logic_rule: JSON.stringify({
      trigger_event: 'lead.created',
      conditions: [],
      actions: [{ action_type: 'send_notification', action_params: { message: 'Novo lead criado' } }]
    }, null, 2),
    social: JSON.stringify({
      channel_type: 'whatsapp',
      social_event: 'message_received',
      actions: [{ action_type: 'auto_reply', action_params: { message: 'Obrigado pelo contato!' } }]
    }, null, 2)
  };

  $effect(() => {
    if (automationType && configTemplates[automationType]) {
      configJson = configTemplates[automationType];
    }
  });
</script>

<svelte:head>
  <title>Nova Automação — TalkHub CRM</title>
</svelte:head>

<div class="mx-auto max-w-2xl space-y-6 p-6">
  <div class="flex items-center gap-3">
    <Button href="/automations" variant="ghost" size="icon" class="size-8">
      <ArrowLeft class="size-4" />
    </Button>
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Nova Automação</h1>
      <p class="text-muted-foreground text-sm">Configure uma nova automação para sua organização.</p>
    </div>
  </div>

  <form method="POST" action="?/create" use:enhance class="space-y-5 rounded-lg border p-6">
    <div class="space-y-2">
      <Label for="name">Nome</Label>
      <Input id="name" name="name" bind:value={name} placeholder="Ex: Notificar novos leads" required />
    </div>

    <div class="space-y-2">
      <Label for="automation_type">Tipo</Label>
      <select
        id="automation_type"
        name="automation_type"
        bind:value={automationType}
        class="border-input bg-background ring-offset-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
        required
      >
        <option value="" disabled>Selecione o tipo...</option>
        <option value="routine">Rotina (Agendada)</option>
        <option value="logic_rule">Regra Lógica (Evento)</option>
        <option value="social">Social (Redes Sociais)</option>
      </select>
    </div>

    {#if automationType}
      <div class="space-y-2">
        <Label for="config_json">Configuração (JSON)</Label>
        <Textarea
          id="config_json"
          name="config_json"
          bind:value={configJson}
          rows={12}
          class="font-mono text-xs"
          placeholder={'{}'}
        />
        <p class="text-muted-foreground text-xs">
          {#if automationType === 'routine'}
            Campos: schedule_cron (minutos ou crontab), action_type, action_params
          {:else if automationType === 'logic_rule'}
            Campos: trigger_event, conditions (field, operator, value), actions
          {:else if automationType === 'social'}
            Campos: channel_type, social_event, actions
          {/if}
        </p>
      </div>
    {/if}

    <div class="flex justify-end gap-3 pt-2">
      <Button href="/automations" variant="outline">Cancelar</Button>
      <Button type="submit" class="gap-2" disabled={!name || !automationType}>
        <Zap class="size-4" />
        Criar Automação
      </Button>
    </div>
  </form>
</div>
