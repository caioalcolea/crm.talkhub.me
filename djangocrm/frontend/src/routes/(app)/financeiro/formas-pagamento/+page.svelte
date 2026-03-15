<script>
  import { enhance } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Plus, Pencil, Trash2 } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';

  let { data } = $props();
  let showCreateModal = $state(false);
  let showEditModal = $state(false);
  let newNome = $state('');
  let editingForma = $state(null);
  let editNome = $state('');

  function openEdit(forma) {
    editingForma = forma;
    editNome = forma.nome;
    showEditModal = true;
  }
</script>

<div class="space-y-4 p-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Formas de Pagamento</h1>
      <p class="text-muted-foreground text-sm">Configure as formas de pagamento disponíveis</p>
    </div>
    <Button onclick={() => { newNome = ''; showCreateModal = true; }}>
      <Plus class="mr-1.5 h-4 w-4" />
      Nova Forma
    </Button>
  </div>

  <div class="overflow-x-auto rounded-lg border">
    <table class="w-full text-sm">
      <thead>
        <tr class="bg-muted/50 border-b">
          <th class="px-4 py-2.5 text-left font-medium">Nome</th>
          <th class="px-4 py-2.5 text-left font-medium">Status</th>
          <th class="px-4 py-2.5 text-right font-medium">Ações</th>
        </tr>
      </thead>
      <tbody>
        {#each data.formas as forma (forma.id)}
          <tr class="border-b">
            <td class="px-4 py-2.5 font-medium">{forma.nome}</td>
            <td class="px-4 py-2.5">
              <form method="POST" action="?/toggle" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
                <input type="hidden" name="id" value={forma.id} />
                <input type="hidden" name="is_active" value={String(forma.is_active)} />
                <button
                  type="submit"
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {forma.is_active
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                    : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}"
                >
                  {forma.is_active ? 'Ativo' : 'Inativo'}
                </button>
              </form>
            </td>
            <td class="px-4 py-2.5 text-right">
              <div class="inline-flex items-center gap-1">
                <Button variant="ghost" size="sm" class="h-7 px-2" onclick={() => openEdit(forma)}>
                  <Pencil class="h-3.5 w-3.5" />
                </Button>
                <form method="POST" action="?/delete" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
                  <input type="hidden" name="id" value={forma.id} />
                  <Button variant="ghost" size="sm" class="text-destructive h-7 px-2" type="submit">
                    <Trash2 class="h-3.5 w-3.5" />
                  </Button>
                </form>
              </div>
            </td>
          </tr>
        {:else}
          <tr>
            <td colspan="3" class="text-muted-foreground px-4 py-12 text-center">
              Nenhuma forma de pagamento cadastrada.
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

<!-- Create Modal -->
<Dialog.Root bind:open={showCreateModal}>
  <Dialog.Content class="max-w-sm">
    <Dialog.Header>
      <Dialog.Title>Nova Forma de Pagamento</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/create" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showCreateModal = false; } await update(); invalidateAll(); }; }}>
      <div class="space-y-3">
        <div>
          <label for="create-nome" class="text-sm font-medium">Nome *</label>
          <input
            id="create-nome"
            name="nome"
            type="text"
            required
            placeholder="Ex: PIX, Boleto, Cartão"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm"
          />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showCreateModal = false)}>Cancelar</Button>
          <Button type="submit">Criar</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<!-- Edit Modal -->
<Dialog.Root bind:open={showEditModal}>
  <Dialog.Content class="max-w-sm">
    <Dialog.Header>
      <Dialog.Title>Editar Forma de Pagamento</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/edit" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showEditModal = false; } await update(); invalidateAll(); }; }}>
      <input type="hidden" name="id" value={editingForma?.id || ''} />
      <div class="space-y-3">
        <div>
          <label for="edit-nome" class="text-sm font-medium">Nome *</label>
          <input
            id="edit-nome"
            name="nome"
            type="text"
            required
            bind:value={editNome}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm"
          />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showEditModal = false)}>Cancelar</Button>
          <Button type="submit">Salvar</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>
