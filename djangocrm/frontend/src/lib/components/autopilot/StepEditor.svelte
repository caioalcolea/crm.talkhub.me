<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { Plus, Trash2 } from '@lucide/svelte';
  import VariablePicker from './VariablePicker.svelte';

  let { steps = $bindable([]) } = $props();

  if (steps.length === 0) {
    steps = [{ step_order: 1, channel: 'email', subject: '', body_template: '', delay_hours: 0 }];
  }

  function addStep() {
    steps = [
      ...steps,
      { step_order: steps.length + 1, channel: 'email', subject: '', body_template: '', delay_hours: 24 }
    ];
  }

  function removeStep(i) {
    steps = steps.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, step_order: idx + 1 }));
  }

  function updateStep(i, key, value) {
    steps = steps.map((s, idx) => idx === i ? { ...s, [key]: value } : s);
  }

  function insertVariable(i, varStr) {
    const current = steps[i].body_template || '';
    updateStep(i, 'body_template', current + varStr);
  }
</script>

<div class="space-y-1">
  {#each steps as step, i (step.step_order)}
    <!-- Timeline connector -->
    {#if i > 0}
      <div class="flex items-center gap-3 py-1">
        <div class="flex w-8 justify-center">
          <div class="h-6 w-0.5 bg-border"></div>
        </div>
        <div class="flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1">
          <span class="text-muted-foreground text-xs">Esperar</span>
          <Input
            type="number"
            min="0"
            class="h-6 w-16 text-center text-xs"
            value={step.delay_hours}
            oninput={(e) => updateStep(i, 'delay_hours', parseInt(e.target.value) || 0)}
          />
          <span class="text-muted-foreground text-xs">h</span>
        </div>
      </div>
    {/if}

    <!-- Step card -->
    <div class="flex gap-3">
      <!-- Timeline node -->
      <div class="flex flex-col items-center pt-4">
        <div class="flex h-8 w-8 items-center justify-center rounded-full border-2 border-primary bg-primary/10 text-xs font-bold text-primary">
          {step.step_order}
        </div>
        {#if i < steps.length - 1}
          <div class="flex-1 w-0.5 bg-border mt-1"></div>
        {/if}
      </div>

      <!-- Step content -->
      <div class="flex-1 space-y-3 rounded-md border p-3">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium">Etapa {step.step_order}</span>
          <div class="flex items-center gap-1">
            <VariablePicker moduleKey="campaigns" onInsert={(v) => insertVariable(i, v)} />
            {#if steps.length > 1}
              <Button type="button" variant="ghost" size="sm" class="text-destructive h-7 px-2" onclick={() => removeStep(i)}>
                <Trash2 class="size-3.5" />
              </Button>
            {/if}
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1">
            <Label class="text-xs">Canal</Label>
            <select
              value={step.channel}
              onchange={(e) => updateStep(i, 'channel', e.target.value)}
              class="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm"
            >
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>
          {#if i > 0}
            <div class="space-y-1">
              <Label class="text-xs">Atraso (horas)</Label>
              <Input
                type="number"
                min="0"
                value={step.delay_hours}
                oninput={(e) => updateStep(i, 'delay_hours', parseInt(e.target.value) || 0)}
              />
            </div>
          {/if}
        </div>

        {#if step.channel === 'email'}
          <div class="space-y-1">
            <Label class="text-xs">Assunto</Label>
            <Input
              value={step.subject || ''}
              oninput={(e) => updateStep(i, 'subject', e.target.value)}
              placeholder="Assunto do email"
            />
          </div>
        {/if}

        <div class="space-y-1">
          <Label class="text-xs">Mensagem</Label>
          <Textarea
            value={step.body_template || ''}
            oninput={(e) => updateStep(i, 'body_template', e.target.value)}
            rows={3}
            placeholder={'Olá {{contact.first_name}}...'}
          />
        </div>
      </div>
    </div>
  {/each}

  <div class="flex justify-center pt-2">
    <Button type="button" variant="outline" size="sm" class="gap-1.5" onclick={addStep}>
      <Plus class="size-3.5" /> Adicionar Etapa
    </Button>
  </div>
</div>
