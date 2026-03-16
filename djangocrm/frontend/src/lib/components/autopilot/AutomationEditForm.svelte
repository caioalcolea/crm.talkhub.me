<script>
  import { apiRequest } from '$lib/api.js';
  import { toast } from 'svelte-sonner';
  import { invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { Save, X } from '@lucide/svelte';

  let { automation, onSaved = () => {}, onCancel = () => {} } = $props();

  let name = $state(automation.name || '');
  let configJson = $state(
    typeof automation.config_json === 'string'
      ? automation.config_json
      : JSON.stringify(automation.config_json || {}, null, 2)
  );
  let saving = $state(false);

  async function handleSave() {
    if (!name.trim()) {
      toast.error('Nome é obrigatório.');
      return;
    }

    let parsedConfig = {};
    try {
      parsedConfig = JSON.parse(configJson);
    } catch {
      toast.error('Configuração JSON inválida.');
      return;
    }

    saving = true;
    try {
      await apiRequest(`/automations/${automation.id}/`, {
        method: 'PATCH',
        body: { name: name.trim(), config_json: parsedConfig }
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

  <div class="space-y-2">
    <Label for="edit-auto-config-{automation.id}">Configuração (JSON)</Label>
    <Textarea
      id="edit-auto-config-{automation.id}"
      bind:value={configJson}
      rows={8}
      class="font-mono text-xs"
    />
  </div>

  <div class="flex justify-end gap-2">
    <Button variant="outline" size="sm" onclick={onCancel}>Cancelar</Button>
    <Button size="sm" class="gap-1.5" onclick={handleSave} disabled={saving}>
      <Save class="size-3.5" />
      {saving ? 'Salvando...' : 'Salvar'}
    </Button>
  </div>
</div>
