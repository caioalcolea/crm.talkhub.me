<script>
  import { apiRequest } from '$lib/api.js';
  import { toast } from 'svelte-sonner';
  import { invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';
  import { Save, X } from '@lucide/svelte';
  import VariablePicker from './VariablePicker.svelte';

  let { template = null, onSaved = () => {}, onCancel = () => {} } = $props();

  const isEdit = !!template;

  let name = $state(template?.name || '');
  let category = $state(template?.category || 'operational');
  let moduleKey = $state(template?.module_key || 'leads');
  let templateType = $state(template?.template_type || 'rule');
  let messageTemplate = $state(template?.message_template || '');
  let configTemplate = $state(
    template?.config_template ? JSON.stringify(template.config_template, null, 2) : '{}'
  );
  let saving = $state(false);

  const CATEGORIES = [
    { value: 'cobranca', label: 'Cobrança' },
    { value: 'follow_up', label: 'Follow-up' },
    { value: 'onboarding', label: 'Onboarding' },
    { value: 'sla', label: 'SLA' },
    { value: 'nurture', label: 'Nurture' },
    { value: 'operational', label: 'Operacional' },
  ];

  const MODULES = [
    { value: 'financeiro', label: 'Financeiro' },
    { value: 'leads', label: 'Leads' },
    { value: 'cases', label: 'Chamados' },
    { value: 'tasks', label: 'Tarefas' },
    { value: 'invoices', label: 'Faturas' },
    { value: 'orders', label: 'Pedidos' },
    { value: 'opportunity', label: 'Negócios' },
  ];

  const TYPES = [
    { value: 'reminder', label: 'Lembrete' },
    { value: 'rule', label: 'Regra' },
    { value: 'campaign', label: 'Campanha' },
  ];

  function insertVariable(v) {
    messageTemplate += v;
  }

  async function handleSave() {
    if (!name.trim()) {
      toast.error('Nome é obrigatório.');
      return;
    }

    let parsedConfig = {};
    try {
      parsedConfig = JSON.parse(configTemplate);
    } catch {
      toast.error('Config JSON inválido.');
      return;
    }

    saving = true;
    try {
      const body = {
        name: name.trim(),
        category,
        module_key: moduleKey,
        template_type: templateType,
        message_template: messageTemplate,
        config_template: parsedConfig,
      };

      if (isEdit) {
        await apiRequest(`/assistant/templates/${template.id}/`, { method: 'PATCH', body });
        toast.success('Modelo atualizado.');
      } else {
        await apiRequest('/assistant/templates/', { method: 'POST', body });
        toast.success('Modelo criado.');
      }
      onSaved();
      invalidateAll();
    } catch (err) {
      toast.error(err?.message || 'Erro ao salvar modelo.');
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-4 rounded-lg border border-l-4 border-l-primary p-5">
  <div class="flex items-center justify-between">
    <h3 class="font-semibold">{isEdit ? 'Editar Modelo' : 'Novo Modelo'}</h3>
    <Button variant="ghost" size="sm" onclick={onCancel}>
      <X class="size-4" />
    </Button>
  </div>

  <div class="grid gap-4 sm:grid-cols-2">
    <div class="space-y-2">
      <Label>Nome</Label>
      <Input bind:value={name} placeholder="Ex: Follow-up de lead frio" required />
    </div>

    <div class="space-y-2">
      <Label>Categoria</Label>
      <select
        bind:value={category}
        class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
      >
        {#each CATEGORIES as cat}
          <option value={cat.value}>{cat.label}</option>
        {/each}
      </select>
    </div>

    <div class="space-y-2">
      <Label>Módulo</Label>
      <select
        bind:value={moduleKey}
        class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
      >
        {#each MODULES as mod}
          <option value={mod.value}>{mod.label}</option>
        {/each}
      </select>
    </div>

    <div class="space-y-2">
      <Label>Tipo</Label>
      <select
        bind:value={templateType}
        class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
      >
        {#each TYPES as t}
          <option value={t.value}>{t.label}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="space-y-2">
    <div class="flex items-center justify-between">
      <Label>Mensagem Template</Label>
      <VariablePicker {moduleKey} onInsert={insertVariable} />
    </div>
    <Textarea bind:value={messageTemplate} rows={5} placeholder="Olá {{contact_name}}, lembrete sobre..." />
  </div>

  <div class="space-y-2">
    <Label>Config Template (JSON)</Label>
    <Textarea bind:value={configTemplate} rows={4} class="font-mono text-xs" placeholder={'{}'} />
  </div>

  <div class="flex justify-end gap-3">
    <Button variant="outline" size="sm" onclick={onCancel}>Cancelar</Button>
    <Button size="sm" class="gap-1.5" onclick={handleSave} disabled={saving}>
      <Save class="size-3.5" />
      {saving ? 'Salvando...' : 'Salvar'}
    </Button>
  </div>
</div>
