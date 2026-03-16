<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Zap, X } from '@lucide/svelte';
  import RuleBuilder from './RuleBuilder.svelte';

  let { onCreated = () => {}, onCancel = () => {} } = $props();

  let name = $state('');
  let automationType = $state('');
  let configObject = $state({});
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
          configObject = {};
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
      <RuleBuilder {automationType} bind:config={configObject} />
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
