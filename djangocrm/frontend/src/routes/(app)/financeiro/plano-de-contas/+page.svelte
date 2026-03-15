<script>
  import { enhance } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Plus, ChevronDown, ChevronRight, Archive, Lock, Pencil, RotateCcw } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';

  let { data } = $props();

  let showGrupoModal = $state(false);
  let showContaModal = $state(false);
  let showEditGrupoModal = $state(false);
  let showEditContaModal = $state(false);
  let showArchived = $state(false);
  let selectedGrupoId = $state('');
  let expandedGrupos = $state({});

  let grupoForm = $state({ codigo: '', nome: '', descricao: '', ordem: 0, color: '#6B7280', applies_to: 'AMBOS' });
  let contaForm = $state({ grupo: '', nome: '', descricao: '' });
  let editGrupoForm = $state({ id: '', codigo: '', nome: '', descricao: '', ordem: 0, color: '#6B7280', applies_to: 'AMBOS' });
  let editContaForm = $state({ id: '', nome: '', descricao: '' });

  const APPLIES_TO_LABELS = { AMBOS: 'Ambos', PAGAR: 'Pagar', RECEBER: 'Receber' };
  const APPLIES_TO_COLORS = { PAGAR: 'text-red-600 bg-red-50', RECEBER: 'text-green-600 bg-green-50', AMBOS: 'text-gray-600 bg-gray-50' };

  let activeGrupos = $derived((data.grupos || []).filter(g => g.is_active));
  let archivedGrupos = $derived((data.grupos || []).filter(g => !g.is_active));

  function toggleGrupo(id) {
    expandedGrupos = { ...expandedGrupos, [id]: !expandedGrupos[id] };
  }

  function openContaModal(grupoId) {
    selectedGrupoId = grupoId;
    contaForm = { grupo: grupoId, nome: '', descricao: '' };
    showContaModal = true;
  }

  function openEditGrupo(grupo) {
    editGrupoForm = {
      id: grupo.id,
      codigo: grupo.codigo,
      nome: grupo.nome,
      descricao: grupo.descricao || '',
      ordem: grupo.ordem,
      color: grupo.color || '#6B7280',
      applies_to: grupo.applies_to || 'AMBOS'
    };
    showEditGrupoModal = true;
  }

  function openEditConta(conta) {
    editContaForm = {
      id: conta.id,
      nome: conta.nome,
      descricao: conta.descricao || ''
    };
    showEditContaModal = true;
  }
</script>

<PageHeader title="Centro de Custo" subtitle="Organize seus centros de custo em grupos hierárquicos">
  {#snippet actions()}
    <Button onclick={() => { grupoForm = { codigo: '', nome: '', descricao: '', ordem: 0, color: '#6B7280', applies_to: 'AMBOS' }; showGrupoModal = true; }}>
      <Plus class="mr-1.5 h-4 w-4" />
      Novo Grupo
    </Button>
  {/snippet}
</PageHeader>

<div class="space-y-4 p-4 md:p-6">
  <!-- Active Groups Tree View -->
  <div class="space-y-2">
    {#each activeGrupos as grupo (grupo.id)}
      <div class="rounded-lg border">
        <!-- Grupo Header -->
        <div class="flex items-center justify-between px-4 py-3">
          <button
            type="button"
            class="flex flex-1 items-center gap-2 text-left"
            onclick={() => toggleGrupo(grupo.id)}
          >
            {#if expandedGrupos[grupo.id]}
              <ChevronDown class="h-4 w-4" />
            {:else}
              <ChevronRight class="h-4 w-4" />
            {/if}
            <span
              class="inline-block h-3 w-3 rounded-full flex-shrink-0"
              style="background-color: {grupo.color || '#6B7280'}"
            ></span>
            <span class="text-muted-foreground text-sm font-mono">{grupo.codigo}</span>
            <span class="font-semibold">{grupo.nome}</span>
            <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium {APPLIES_TO_COLORS[grupo.applies_to] || APPLIES_TO_COLORS.AMBOS}">
              {APPLIES_TO_LABELS[grupo.applies_to] || 'Ambos'}
            </span>
            <span class="text-muted-foreground text-xs">
              ({(grupo.contas || []).filter(c => c.is_active).length} conta{(grupo.contas || []).filter(c => c.is_active).length !== 1 ? 's' : ''})
            </span>
            {#if grupo.is_system_default}
              <Lock class="h-3 w-3 text-muted-foreground" />
            {/if}
          </button>
          <div class="flex items-center gap-1">
            <Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => openContaModal(grupo.id)}>
              <Plus class="mr-1 h-3 w-3" /> Conta
            </Button>
            <Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => openEditGrupo(grupo)}>
              <Pencil class="h-3 w-3" />
            </Button>
            {#if !grupo.is_system_default}
              <form method="POST" action="?/archiveGrupo" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
                <input type="hidden" name="id" value={grupo.id} />
                <Button variant="ghost" size="sm" class="text-orange-600 h-7 px-2" type="submit" title="Arquivar grupo">
                  <Archive class="h-3 w-3" />
                </Button>
              </form>
            {/if}
          </div>
        </div>

        <!-- Contas -->
        {#if expandedGrupos[grupo.id] && grupo.contas?.length > 0}
          <div class="border-t px-4 py-2">
            {#each (grupo.contas || []).filter(c => c.is_active) as conta (conta.id)}
              <div class="flex items-center justify-between py-1.5 pl-6">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium">{conta.nome}</span>
                  {#if conta.code}
                    <span class="text-muted-foreground text-xs font-mono">{conta.code}</span>
                  {/if}
                  {#if conta.descricao}
                    <span class="text-muted-foreground text-xs">{conta.descricao}</span>
                  {/if}
                  {#if conta.is_system_default}
                    <Lock class="h-2.5 w-2.5 text-muted-foreground" />
                  {/if}
                </div>
                <div class="flex items-center gap-1">
                  <Button variant="ghost" size="sm" class="h-6 px-1.5" onclick={() => openEditConta(conta)}>
                    <Pencil class="h-2.5 w-2.5" />
                  </Button>
                  {#if !conta.is_system_default}
                    <form method="POST" action="?/archiveConta" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
                      <input type="hidden" name="id" value={conta.id} />
                      <Button variant="ghost" size="sm" class="text-orange-600 h-6 px-1.5" type="submit" title="Arquivar conta">
                        <Archive class="h-2.5 w-2.5" />
                      </Button>
                    </form>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {:else}
      <div class="text-muted-foreground py-12 text-center">
        Nenhum grupo cadastrado. Crie o primeiro grupo para começar.
      </div>
    {/each}
  </div>

  <!-- Archived section -->
  {#if archivedGrupos.length > 0}
    <div class="border-t pt-4">
      <button
        type="button"
        class="text-muted-foreground flex items-center gap-2 text-sm hover:text-foreground"
        onclick={() => (showArchived = !showArchived)}
      >
        {#if showArchived}
          <ChevronDown class="h-4 w-4" />
        {:else}
          <ChevronRight class="h-4 w-4" />
        {/if}
        Arquivados ({archivedGrupos.length} grupo{archivedGrupos.length !== 1 ? 's' : ''})
      </button>
      {#if showArchived}
        <div class="mt-2 space-y-2 opacity-60">
          {#each archivedGrupos as grupo (grupo.id)}
            <div class="rounded-lg border border-dashed">
              <div class="flex items-center justify-between px-4 py-2">
                <div class="flex items-center gap-2">
                  <span
                    class="inline-block h-3 w-3 rounded-full flex-shrink-0"
                    style="background-color: {grupo.color || '#6B7280'}"
                  ></span>
                  <span class="text-muted-foreground text-sm font-mono">{grupo.codigo}</span>
                  <span class="font-medium">{grupo.nome}</span>
                  <span class="text-xs text-muted-foreground italic">arquivado</span>
                </div>
                <form method="POST" action="?/restoreGrupo" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
                  <input type="hidden" name="id" value={grupo.id} />
                  <Button variant="ghost" size="sm" class="text-green-600 h-7 px-2" type="submit" title="Restaurar grupo">
                    <RotateCcw class="h-3 w-3" />
                  </Button>
                </form>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Create Grupo Modal -->
<Dialog.Root bind:open={showGrupoModal}>
  <Dialog.Content class="max-w-md">
    <Dialog.Header>
      <Dialog.Title>Novo Grupo</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/createGrupo" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showGrupoModal = false; } await update(); invalidateAll(); }; }}>
      <div class="space-y-3">
        <div>
          <label for="codigo" class="text-sm font-medium">Código *</label>
          <input id="codigo" name="codigo" type="text" required placeholder="Ex: REC-01"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="nome" class="text-sm font-medium">Nome *</label>
          <input id="nome" name="nome" type="text" required placeholder="Ex: Receita de Vendas"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="descricao" class="text-sm font-medium">Descrição</label>
          <input id="descricao" name="descricao" type="text"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="ordem" class="text-sm font-medium">Ordem</label>
            <input id="ordem" name="ordem" type="number" value="0"
              class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
          </div>
          <div>
            <label for="color" class="text-sm font-medium">Cor</label>
            <input id="color" name="color" type="color" value="#6B7280"
              class="mt-1 h-9 w-full rounded-md border cursor-pointer" />
          </div>
          <div>
            <label for="applies_to" class="text-sm font-medium">Tipo</label>
            <select id="applies_to" name="applies_to"
              class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm">
              <option value="AMBOS">Ambos</option>
              <option value="PAGAR">Pagar</option>
              <option value="RECEBER">Receber</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showGrupoModal = false)}>Cancelar</Button>
          <Button type="submit">Criar Grupo</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<!-- Edit Grupo Modal -->
<Dialog.Root bind:open={showEditGrupoModal}>
  <Dialog.Content class="max-w-md">
    <Dialog.Header>
      <Dialog.Title>Editar Grupo</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/editGrupo" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showEditGrupoModal = false; } await update(); invalidateAll(); }; }}>
      <input type="hidden" name="id" value={editGrupoForm.id} />
      <div class="space-y-3">
        <div>
          <label for="edit_codigo" class="text-sm font-medium">Código *</label>
          <input id="edit_codigo" name="codigo" type="text" required bind:value={editGrupoForm.codigo}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="edit_nome" class="text-sm font-medium">Nome *</label>
          <input id="edit_nome" name="nome" type="text" required bind:value={editGrupoForm.nome}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="edit_descricao" class="text-sm font-medium">Descrição</label>
          <input id="edit_descricao" name="descricao" type="text" bind:value={editGrupoForm.descricao}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="edit_ordem" class="text-sm font-medium">Ordem</label>
            <input id="edit_ordem" name="ordem" type="number" bind:value={editGrupoForm.ordem}
              class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
          </div>
          <div>
            <label for="edit_color" class="text-sm font-medium">Cor</label>
            <input id="edit_color" name="color" type="color" bind:value={editGrupoForm.color}
              class="mt-1 h-9 w-full rounded-md border cursor-pointer" />
          </div>
          <div>
            <label for="edit_applies_to" class="text-sm font-medium">Tipo</label>
            <select id="edit_applies_to" name="applies_to" bind:value={editGrupoForm.applies_to}
              class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm">
              <option value="AMBOS">Ambos</option>
              <option value="PAGAR">Pagar</option>
              <option value="RECEBER">Receber</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showEditGrupoModal = false)}>Cancelar</Button>
          <Button type="submit">Salvar</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<!-- Create Conta Modal -->
<Dialog.Root bind:open={showContaModal}>
  <Dialog.Content class="max-w-md">
    <Dialog.Header>
      <Dialog.Title>Nova Conta</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/createConta" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showContaModal = false; } await update(); invalidateAll(); }; }}>
      <input type="hidden" name="grupo" value={selectedGrupoId} />
      <div class="space-y-3">
        <div>
          <label for="conta_nome" class="text-sm font-medium">Nome *</label>
          <input id="conta_nome" name="nome" type="text" required placeholder="Ex: Vendas de Produtos"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="conta_descricao" class="text-sm font-medium">Descrição</label>
          <input id="conta_descricao" name="descricao" type="text"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showContaModal = false)}>Cancelar</Button>
          <Button type="submit">Criar Conta</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<!-- Edit Conta Modal -->
<Dialog.Root bind:open={showEditContaModal}>
  <Dialog.Content class="max-w-md">
    <Dialog.Header>
      <Dialog.Title>Editar Conta</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/editConta" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showEditContaModal = false; } await update(); invalidateAll(); }; }}>
      <input type="hidden" name="id" value={editContaForm.id} />
      <div class="space-y-3">
        <div>
          <label for="edit_conta_nome" class="text-sm font-medium">Nome *</label>
          <input id="edit_conta_nome" name="nome" type="text" required bind:value={editContaForm.nome}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="edit_conta_descricao" class="text-sm font-medium">Descrição</label>
          <input id="edit_conta_descricao" name="descricao" type="text" bind:value={editContaForm.descricao}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showEditContaModal = false)}>Cancelar</Button>
          <Button type="submit">Salvar</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>
