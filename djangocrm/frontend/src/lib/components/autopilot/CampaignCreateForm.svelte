<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { Megaphone, X } from '@lucide/svelte';
  import StepEditor from './StepEditor.svelte';
  import VariablePicker from './VariablePicker.svelte';
  import AICopilot from './AICopilot.svelte';

  let { onCreated = () => {}, onCancel = () => {} } = $props();

  let name = $state('');
  let campaignType = $state('');
  let subject = $state('');
  let bodyTemplate = $state('');

  let steps = $state([
    { step_order: 1, channel: 'email', subject: '', body_template: '', delay_hours: 0 }
  ]);

  let stepsJson = $derived(JSON.stringify(steps));
  let canSubmit = $derived(name.trim() !== '' && campaignType !== '');

  function insertBodyVar(v) {
    bodyTemplate += v;
  }

  function handleAIGenerated(result) {
    if (result.name) name = result.name;
    if (result.subject) subject = result.subject;
    if (result.body_template) bodyTemplate = result.body_template;
    if (result.steps && Array.isArray(result.steps)) steps = result.steps;
  }
</script>

<div class="rounded-lg border border-l-4 border-l-primary p-5 space-y-4">
  <div class="flex items-center justify-between">
    <h3 class="font-semibold">Nova Campanha</h3>
    <Button variant="ghost" size="sm" onclick={onCancel}>
      <X class="size-4" />
    </Button>
  </div>

  <form
    method="POST"
    action="?/createCampaign"
    use:enhance={() => {
      return async ({ result, update }) => {
        if (result.type === 'success') {
          toast.success('Campanha criada com sucesso.');
          name = '';
          campaignType = '';
          subject = '';
          bodyTemplate = '';
          steps = [{ step_order: 1, channel: 'email', subject: '', body_template: '', delay_hours: 0 }];
          onCreated();
          await update();
        } else if (result.type === 'failure') {
          toast.error(result.data?.error || 'Erro ao criar campanha.');
        }
      };
    }}
    class="space-y-4"
  >
    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-2">
        <Label for="create-camp-name">Nome da Campanha</Label>
        <Input id="create-camp-name" name="name" bind:value={name} placeholder="Ex: Black Friday 2026" required />
      </div>

      <div class="space-y-2">
        <Label for="create-camp-type">Tipo</Label>
        <select
          id="create-camp-type"
          name="campaign_type"
          bind:value={campaignType}
          class="border-input bg-background ring-offset-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
          required
        >
          <option value="" disabled>Selecione o tipo...</option>
          <option value="email_blast">Email Blast</option>
          <option value="whatsapp_broadcast">WhatsApp Broadcast</option>
          <option value="nurture_sequence">Nurture Sequence</option>
        </select>
      </div>
    </div>

    {#if campaignType}
      <AICopilot
        type="campaign"
        context={{ campaign_type: campaignType }}
        onGenerated={handleAIGenerated}
      />
    {/if}

    {#if campaignType === 'email_blast'}
      <div class="space-y-2">
        <Label for="create-camp-subject">Assunto do Email</Label>
        <Input id="create-camp-subject" name="subject" bind:value={subject} placeholder="Ex: Oferta especial para você" />
      </div>
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <Label for="create-camp-body">Corpo do Email (HTML)</Label>
          <VariablePicker moduleKey="campaigns" onInsert={insertBodyVar} />
        </div>
        <Textarea
          id="create-camp-body"
          name="body_template"
          bind:value={bodyTemplate}
          rows={8}
          placeholder={'<h1>Olá {{contact.first_name}}</h1>...'}
        />
      </div>
    {/if}

    {#if campaignType === 'whatsapp_broadcast'}
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <Label for="create-camp-wa-body">Mensagem</Label>
          <VariablePicker moduleKey="campaigns" onInsert={insertBodyVar} />
        </div>
        <Textarea
          id="create-camp-wa-body"
          name="body_template"
          bind:value={bodyTemplate}
          rows={5}
          placeholder={'Olá {{contact.first_name}}, temos uma novidade...'}
        />
      </div>
    {/if}

    {#if campaignType === 'nurture_sequence'}
      <input type="hidden" name="body_template" value="" />
      <input type="hidden" name="steps" value={stepsJson} />

      <div class="space-y-3">
        <Label>Etapas da Sequência</Label>
        <StepEditor bind:steps />
      </div>
    {/if}

    <div class="flex justify-end gap-3">
      <Button type="button" variant="outline" size="sm" onclick={onCancel}>Cancelar</Button>
      <Button type="submit" size="sm" class="gap-2" disabled={!canSubmit}>
        <Megaphone class="size-4" />
        Criar Campanha
      </Button>
    </div>
  </form>
</div>
