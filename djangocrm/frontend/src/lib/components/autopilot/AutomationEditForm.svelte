<script>
  import { apiRequest } from '$lib/api.js';
  import { toast } from 'svelte-sonner';
  import { invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Save, X } from '@lucide/svelte';
  import RuleBuilder from './RuleBuilder.svelte';

  let { automation, onSaved = () => {}, onCancel = () => {} } = $props();

  let name = $state(automation.name || '');
  let configObject = $state(
    typeof automation.config_json === 'string'
      ? JSON.parse(automation.config_json || '{}')
      : (automation.config_json || {})
  );
  let saving = $state(false);

  async function handleSave() {
    if (!name.trim()) {
      toast.error('Nome é obrigatório.');
      return;
    }

    saving = true;
    try {
      await apiRequest(`/automations/${automation.id}/`, {
        method: 'PATCH',
        body: { name: name.trim(), config_json: configObject }
      });
      toast.success('Automação atualizada.');
      onSaved();
      invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao atualizar automação.');
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-3 rounded-md border bg-muted/30 p-4">
  <div class="flex items-center justify-between">
    <span class="text-sm font-medium">Editar Automação</span>
    <Button variant="ghost" size="sm" class="h-7 px-2" onclick={onCancel}>
      <X class="size-3.5" />
    </Button>
  </div>

  <div class="space-y-2">
    <Label for="edit-auto-name-{automation.id}">Nome</Label>
    <Input id="edit-auto-name-{automation.id}" bind:value={name} placeholder="Nome da automação" />
  </div>

  <RuleBuilder automationType={automation.automation_type} bind:config={configObject} />

  <div class="flex justify-end gap-2">
    <Button variant="outline" size="sm" onclick={onCancel}>Cancelar</Button>
    <Button size="sm" class="gap-1.5" onclick={handleSave} disabled={saving}>
      <Save class="size-3.5" />
      {saving ? 'Salvando...' : 'Salvar'}
    </Button>
  </div>
</div>
