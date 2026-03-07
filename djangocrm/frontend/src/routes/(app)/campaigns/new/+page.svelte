<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { ArrowLeft, Megaphone, Plus, Trash2 } from '@lucide/svelte';

  let { form } = $props();

  let name = $state('');
  let campaignType = $state('');
  let subject = $state('');
  let bodyTemplate = $state('');

  // Nurture steps
  let steps = $state([
    { step_order: 1, channel: 'email', subject: '', body_template: '', delay_hours: 0 }
  ]);

  $effect(() => {
    if (form?.error) toast.error(form.error);
  });

  function addStep() {
    steps = [
      ...steps,
      {
        step_order: steps.length + 1,
        channel: 'email',
        subject: '',
        body_template: '',
        delay_hours: 24
      }
    ];
  }

  /**
   * @param {number} index
   */
  function removeStep(index) {
    steps = steps
      .filter((_, i) => i !== index)
      .map((s, i) => ({ ...s, step_order: i + 1 }));
  }

  let stepsJson = $derived(JSON.stringify(steps));
  let canSubmit = $derived(name.trim() !== '' && campaignType !== '');

  const variableHints = '{{contact.first_name}}, {{contact.last_name}}, {{contact.email}}, {{contact.organization}}';
</script>

<svelte:head>
  <title>Nova Campanha — TalkHub CRM</title>
</svelte:head>

<div class="mx-auto max-w-3xl space-y-6 p-6">
  <div class="flex items-center gap-3">
    <Button href="/campaigns" variant="ghost" size="icon" class="size-8">
      <ArrowLeft class="size-4" />
    </Button>
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Nova Campanha</h1>
      <p class="text-muted-foreground text-sm">Configure uma nova campanha de marketing.</p>
    </div>
  </div>

  <form method="POST" action="?/create" use:enhance class="space-y-5 rounded-lg border p-6">
    <div class="space-y-2">
      <Label for="name">Nome da Campanha</Label>
      <Input id="name" name="name" bind:value={name} placeholder="Ex: Black Friday 2026" required />
    </div>

    <div class="space-y-2">
      <Label for="campaign_type">Tipo</Label>
      <select
        id="campaign_type"
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

    <!-- Email Blast fields -->
    {#if campaignType === 'email_blast'}
      <div class="space-y-2">
        <Label for="subject">Assunto do Email</Label>
        <Input id="subject" name="subject" bind:value={subject} placeholder="Ex: Oferta especial para você" />
      </div>
      <div class="space-y-2">
        <Label for="body_template">Corpo do Email (HTML)</Label>
        <Textarea
          id="body_template"
          name="body_template"
          bind:value={bodyTemplate}
          rows={10}
          placeholder={'<h1>Olá {{contact.first_name}}</h1>...'}
        />
        <p class="text-muted-foreground text-xs">Variáveis disponíveis: {variableHints}</p>
      </div>
    {/if}

    <!-- WhatsApp Broadcast fields -->
    {#if campaignType === 'whatsapp_broadcast'}
      <div class="space-y-2">
        <Label for="body_template">Mensagem</Label>
        <Textarea
          id="body_template"
          name="body_template"
          bind:value={bodyTemplate}
          rows={6}
          placeholder={'Olá {{contact.first_name}}, temos uma novidade...'}
        />
        <p class="text-muted-foreground text-xs">Variáveis disponíveis: {variableHints}</p>
      </div>
    {/if}

    <!-- Nurture Sequence fields -->
    {#if campaignType === 'nurture_sequence'}
      <input type="hidden" name="body_template" value="" />
      <input type="hidden" name="steps" value={stepsJson} />

      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <Label>Etapas da Sequência</Label>
          <Button type="button" variant="outline" size="sm" class="gap-1.5" onclick={addStep}>
            <Plus class="size-3.5" />
            Adicionar Etapa
          </Button>
        </div>

        {#each steps as step, i (step.step_order)}
          <div class="space-y-3 rounded-md border p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium">Etapa {step.step_order}</span>
              {#if steps.length > 1}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  class="text-destructive h-7 px-2"
                  onclick={() => removeStep(i)}
                >
                  <Trash2 class="size-3.5" />
                </Button>
              {/if}
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <Label>Canal</Label>
                <select
                  bind:value={step.channel}
                  class="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm"
                >
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
              </div>
              <div class="space-y-1">
                <Label>Atraso (horas)</Label>
                <Input
                  type="number"
                  min="0"
                  bind:value={step.delay_hours}
                  placeholder="0"
                />
              </div>
            </div>

            {#if step.channel === 'email'}
              <div class="space-y-1">
                <Label>Assunto</Label>
                <Input bind:value={step.subject} placeholder="Assunto do email" />
              </div>
            {/if}

            <div class="space-y-1">
              <Label>Mensagem</Label>
              <Textarea
                bind:value={step.body_template}
                rows={4}
                placeholder={'Olá {{contact.first_name}}...'}
              />
            </div>
          </div>
        {/each}

        <p class="text-muted-foreground text-xs">Variáveis disponíveis: {variableHints}</p>
      </div>
    {/if}

    <div class="flex justify-end gap-3 pt-2">
      <Button href="/campaigns" variant="outline">Cancelar</Button>
      <Button type="submit" class="gap-2" disabled={!canSubmit}>
        <Megaphone class="size-4" />
        Criar Campanha
      </Button>
    </div>
  </form>
</div>
