<script>
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Textarea } from '$lib/components/ui/textarea/index.js';

  let { actionType = '', params = {}, onchange = () => {} } = $props();

  function set(key, value) {
    const updated = { ...params, [key]: value };
    onchange(updated);
  }
</script>

{#if actionType === 'send_notification'}
  <div class="space-y-2">
    <Label>Mensagem</Label>
    <Textarea value={params.message || ''} oninput={(e) => set('message', e.target.value)} rows={3} placeholder="Mensagem da notificação..." />
  </div>

{:else if actionType === 'send_email'}
  <div class="space-y-2">
    <Label>Destinatário (email)</Label>
    <Input type="email" value={params.to || ''} oninput={(e) => set('to', e.target.value)} placeholder="email@exemplo.com" />
  </div>
  <div class="space-y-2">
    <Label>Assunto</Label>
    <Input value={params.subject || ''} oninput={(e) => set('subject', e.target.value)} placeholder="Assunto do email" />
  </div>
  <div class="space-y-2">
    <Label>Corpo</Label>
    <Textarea value={params.body || ''} oninput={(e) => set('body', e.target.value)} rows={4} placeholder="Corpo do email..." />
  </div>

{:else if actionType === 'create_task'}
  <div class="space-y-2">
    <Label>Título da Tarefa</Label>
    <Input value={params.title || ''} oninput={(e) => set('title', e.target.value)} placeholder="Título" />
  </div>
  <div class="space-y-2">
    <Label>Descrição</Label>
    <Textarea value={params.description || ''} oninput={(e) => set('description', e.target.value)} rows={3} placeholder="Descrição (opcional)" />
  </div>
  <div class="space-y-2">
    <Label>Prioridade</Label>
    <select
      value={params.priority || 'Normal'}
      onchange={(e) => set('priority', e.target.value)}
      class="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm"
    >
      <option value="Alta">Alta</option>
      <option value="Normal">Normal</option>
      <option value="Baixa">Baixa</option>
    </select>
  </div>

{:else if actionType === 'update_field'}
  <div class="grid grid-cols-2 gap-3">
    <div class="space-y-2">
      <Label>Módulo</Label>
      <select
        value={params.app_label || ''}
        onchange={(e) => set('app_label', e.target.value)}
        class="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm"
      >
        <option value="">Selecione...</option>
        <option value="leads">Leads</option>
        <option value="contacts">Contatos</option>
        <option value="opportunity">Negócios</option>
        <option value="cases">Chamados</option>
        <option value="tasks">Tarefas</option>
      </select>
    </div>
    <div class="space-y-2">
      <Label>Campo</Label>
      <Input value={params.field_name || ''} oninput={(e) => set('field_name', e.target.value)} placeholder="Ex: status" />
    </div>
  </div>
  <div class="space-y-2">
    <Label>Novo Valor</Label>
    <Input value={params.new_value || ''} oninput={(e) => set('new_value', e.target.value)} placeholder="Valor a definir" />
  </div>

{:else if actionType === 'auto_reply'}
  <div class="space-y-2">
    <Label>Mensagem de Resposta</Label>
    <Textarea value={params.message || ''} oninput={(e) => set('message', e.target.value)} rows={3} placeholder="Resposta automática..." />
  </div>

{:else if actionType === 'assign_to_user'}
  <div class="space-y-2">
    <Label>ID do Usuário</Label>
    <Input value={params.user_id || ''} oninput={(e) => set('user_id', e.target.value)} placeholder="UUID do usuário" />
  </div>

{:else if actionType === 'create_lead'}
  <div class="space-y-2">
    <Label>Título do Lead (opcional)</Label>
    <Input value={params.title || ''} oninput={(e) => set('title', e.target.value)} placeholder="Novo lead de..." />
  </div>

{:else if actionType === 'add_tag'}
  <div class="space-y-2">
    <Label>Nome da Tag</Label>
    <Input value={params.tag_name || ''} oninput={(e) => set('tag_name', e.target.value)} placeholder="Ex: vip, urgente" />
  </div>

{:else if actionType}
  <p class="text-muted-foreground text-xs italic">Tipo de ação "{actionType}" — configure os parâmetros manualmente.</p>
{/if}
