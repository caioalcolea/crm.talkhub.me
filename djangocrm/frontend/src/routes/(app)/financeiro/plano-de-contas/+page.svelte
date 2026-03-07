<script>
  import { enhance } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Plus, ChevronDown, ChevronRight, Trash2 } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';

  let { data } = $props();

  let showGrupoModal = $state(false);
  let showContaModal = $state(false);
  let selectedGrupoId = $state('');
  let expandedGrupos = $state({});

  let grupoForm = $state({ codigo: '', nome: '', descricao: '', ordem: 0 });
  let contaForm = $state({ grupo: '', nome: '', descricao: '' });

  function toggleGrupo(id) {
    expandedGrupos = { ...expandedGrupos, [id]: !expandedGrupos[id] };
  }

  function openContaModal(grupoId) {
    selectedGrupoId = grupoId;
    contaForm = { grupo: grupoId, nome: '', descricao: '' };
    showContaModal = true;
  }
</script>

<div class="space-y-4 p-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Centro de Custo</h1>
      <p class="text-muted-foreground text-sm">Organize seus centros de custo em grupos hierárquicos</p>
    </div>
    <Button onclick={() => { grupoForm = { codigo: '', nome: '', descricao: '', ordem: 0 }; showGrupoModal = true; }}>
      <Plus class="mr-1.5 h-4 w-4" />
      Novo Grupo
    </Button>
  </div>

  <!-- Tree View -->
  <div class="space-y-2">
    {#each data.grupos as grupo (grupo.id)}
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
            <span class="text-muted-foreground text-sm font-mono">{grupo.codigo}</span>
            <span class="font-semibold">{grupo.nome}</span>
            <span class="text-muted-foreground text-xs">
              ({(grupo.contas || []).length} conta{(grupo.contas || []).length !== 1 ? 's' : ''})
            </span>
          </button>
          <div class="flex items-center gap-1">
            <Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => openContaModal(grupo.id)}>
              <Plus class="mr-1 h-3 w-3" /> Conta
            </Button>
            <form method="POST" action="?/deleteGrupo" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
              <input type="hidden" name="id" value={grupo.id} />
              <Button variant="ghost" size="sm" class="text-destructive h-7 px-2" type="submit">
                <Trash2 class="h-3 w-3" />
              </Button>
            </form>
          </div>
        </div>

        <!-- Contas -->
        {#if expandedGrupos[grupo.id] && grupo.contas?.length > 0}
          <div class="border-t px-4 py-2">
            {#each grupo.contas as conta (conta.id)}
              <div class="flex items-center justify-between py-1.5 pl-6">
                <div>
                  <span class="text-sm font-medium">{conta.nome}</span>
                  {#if conta.descricao}
                    <span class="text-muted-foreground ml-2 text-xs">{conta.descricao}</span>
                  {/if}
                </div>
                <form method="POST" action="?/deleteConta" use:enhance={() => { return async ({ update }) => { await update(); invalidateAll(); }; }}>
                  <input type="hidden" name="id" value={conta.id} />
                  <Button variant="ghost" size="sm" class="text-destructive h-6 px-1.5" type="submit">
                    <Trash2 class="h-3 w-3" />
                  </Button>
                </form>
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
</div>

<!-- Grupo Modal -->
<Dialog.Root bind:open={showGrupoModal}>
  <Dialog.Content class="max-w-md">
    <Dialog.Header>
      <Dialog.Title>Novo Grupo</Dialog.Title>
    </Dialog.Header>
    <form method="POST" action="?/createGrupo" use:enhance={() => { return async ({ result, update }) => { if (result.type === 'success') { showGrupoModal = false; } await update(); invalidateAll(); }; }}>
      <div class="space-y-3">
        <div>
          <label for="codigo" class="text-sm font-medium">Código *</label>
          <input id="codigo" name="codigo" type="text" required placeholder="Ex: 1.1"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="nome" class="text-sm font-medium">Nome *</label>
          <input id="nome" name="nome" type="text" required placeholder="Ex: Receitas Operacionais"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="descricao" class="text-sm font-medium">Descrição</label>
          <input id="descricao" name="descricao" type="text"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div>
          <label for="ordem" class="text-sm font-medium">Ordem</label>
          <input id="ordem" name="ordem" type="number" value="0"
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm" />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onclick={() => (showGrupoModal = false)}>Cancelar</Button>
          <Button type="submit">Criar Grupo</Button>
        </div>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>

<!-- Conta Modal -->
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
