<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { Zap, X } from '@lucide/svelte';

  let { onCreated = () => {}, onCancel = () => {} } = $props();

  let name = $state('');
  let automationType = $state('');
  let configJson = $state('{}');

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

<div class="rounded-lg border border-l-4 border-l-primary p-5 space-y-4">
  <div class="flex items-center justify-between">
    <h3 class="font-semibold">Nova Automação</h3>
    <Button variant="ghost" size="sm" onclick={onCancel}>
      <X class="size-4" />
    </Button>
  </div>

  <form
    method="POST"
    action="?/createAutomation"
    use:enhance={() => {
      return async ({ result, update }) => {
        if (result.type === 'success') {
          toast.success('Automação criada com sucesso.');
          name = '';
          automationType = '';
          configJson = '{}';
          onCreated();
          await update();
        } else if (result.type === 'failure') {
          toast.error(result.data?.error || 'Erro ao criar automação.');
        }
      };
    }}
    class="space-y-4"
  >
    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-2">
        <Label for="create-auto-name">Nome</Label>
        <Input id="create-auto-name" name="name" bind:value={name} placeholder="Ex: Notificar novos leads" required />
      </div>

      <div class="space-y-2">
        <Label for="create-auto-type">Tipo</Label>
        <select
          id="create-auto-type"
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
    </div>

    {#if automationType}
      <div class="space-y-2">
        <Label for="create-auto-config">Configuração (JSON)</Label>
        <Textarea
          id="create-auto-config"
          name="config_json"
          bind:value={configJson}
          rows={10}
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

    <div class="flex justify-end gap-3">
      <Button type="button" variant="outline" size="sm" onclick={onCancel}>Cancelar</Button>
      <Button type="submit" size="sm" class="gap-2" disabled={!name || !automationType}>
        <Zap class="size-4" />
        Criar Automação
      </Button>
    </div>
  </form>
</div>
