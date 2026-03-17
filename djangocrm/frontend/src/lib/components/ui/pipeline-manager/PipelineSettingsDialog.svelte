<script>
  import { untrack } from 'svelte';
  import {
    GripVertical,
    Plus,
    Trash2,
    Loader2,
    Palette,
    Eye,
    EyeOff,
    Users,
    User
  } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import * as Tabs from '$lib/components/ui/tabs/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';

  /**
   * @type {{
   *   pipeline: any,
   *   teams?: Array<{id: string, name: string}>,
   *   users?: Array<{id: string, name: string, email?: string}>,
   *   open: boolean,
   *   onUpdate?: (id: string, data: any) => Promise<void>,
   *   onDelete?: (id: string) => Promise<void>,
   *   onStageCreate?: (pipelineId: string, data: any) => Promise<any>,
   *   onStageUpdate?: (stageId: string, data: any) => Promise<void>,
   *   onStageDelete?: (stageId: string) => Promise<void>,
   *   onStageReorder?: (pipelineId: string, order: string[]) => Promise<void>,
   *   onConfirmDelete?: (id: string) => void
   * }}
   */
  let {
    pipeline,
    teams = [],
    users = [],
    open = $bindable(false),
    onUpdate,
    onDelete,
    onStageCreate,
    onStageUpdate,
    onStageDelete,
    onStageReorder,
    onConfirmDelete,
    module = 'leads'
  } = $props();

  // Local state
  let pipelineName = $state(pipeline?.name || '');
  let pipelineDescription = $state(pipeline?.description || '');
  let saving = $state(false);
  let addingStageName = $state('');
  let addingStage = $state(false);

  // Local editing state for stage names — decoupled from reactive props
  // Prevents Svelte 5 controlled input from resetting mid-edit
  let editingStageNames = $state({});

  // Visibility state
  let selectedTeams = $state(new Set(pipeline?.visible_to_teams?.map(String) || []));
  let selectedUsers = $state(new Set(pipeline?.visible_to_users?.map(String) || []));

  // Stages from pipeline
  const stages = $derived(pipeline?.stages || []);
  const sortedStages = $derived([...stages].sort((a, b) => a.order - b.order));

  // Tab state
  let activeTab = $state('stages');

  // Drag-and-drop state
  let draggedIndex = $state(-1);
  let dragOverIndex = $state(-1);

  // Stage type options — varies by module
  const stageTypeOptions = $derived.by(() => {
    if (module === 'cases') {
      return [
        { value: 'open', label: 'Aberto' },
        { value: 'closed', label: 'Fechado' },
        { value: 'rejected', label: 'Rejeitado' }
      ];
    }
    if (module === 'tasks') {
      return [
        { value: 'open', label: 'Aberto' },
        { value: 'in_progress', label: 'Em Andamento' },
        { value: 'completed', label: 'Concluído' }
      ];
    }
    // leads, opportunities
    return [
      { value: 'open', label: 'Aberto' },
      { value: 'won', label: 'Ganho' },
      { value: 'lost', label: 'Perdido' }
    ];
  });

  // Preset colors for stages
  const colorPresets = [
    '#6B7280', '#3B82F6', '#8B5CF6', '#EC4899',
    '#F59E0B', '#10B981', '#EF4444', '#06B6D4',
    '#F97316', '#14B8A6'
  ];

  // Sync local state when pipeline prop changes (after invalidateAll).
  // Only track `pipeline` — write to local state inside untrack to avoid loops.
  $effect(() => {
    const p = pipeline;
    untrack(() => {
      if (p) {
        pipelineName = p.name || '';
        pipelineDescription = p.description || '';
        selectedTeams = new Set(p.visible_to_teams?.map(String) || []);
        selectedUsers = new Set(p.visible_to_users?.map(String) || []);
      }
    });
  });

  // Reset local state when dialog closes
  $effect(() => {
    if (!open) {
      editingStageNames = {};
      activeTab = 'stages';
    }
  });

  async function handleSavePipeline() {
    if (!onUpdate) return;
    saving = true;
    try {
      await onUpdate(pipeline.id, {
        name: pipelineName,
        description: pipelineDescription,
        visible_to_teams: [...selectedTeams],
        visible_to_users: [...selectedUsers]
      });
    } catch (err) {
      console.error('Failed to update pipeline:', err);
    } finally {
      saving = false;
    }
  }

  async function handleAddStage() {
    if (!addingStageName.trim() || !onStageCreate) return;
    addingStage = true;
    try {
      await onStageCreate(pipeline.id, {
        name: addingStageName.trim(),
        order: stages.length,
        color: colorPresets[stages.length % colorPresets.length],
        stage_type: 'open'
      });
      addingStageName = '';
    } catch (err) {
      console.error('Failed to create stage:', err);
    } finally {
      addingStage = false;
    }
  }

  async function handleDeleteStage(stageId) {
    if (!onStageDelete) return;
    try {
      await onStageDelete(stageId);
    } catch (err) {
      console.error('Failed to delete stage:', err);
    }
  }

  async function handleStageNameChange(stageId, newName, originalName) {
    if (!onStageUpdate || !newName.trim() || newName.trim() === originalName) return;
    try {
      await onStageUpdate(stageId, { name: newName.trim() });
    } catch (err) {
      console.error('Failed to update stage name:', err);
    }
  }

  async function handleStageColorChange(stageId, color) {
    if (!onStageUpdate) return;
    try {
      await onStageUpdate(stageId, { color });
    } catch (err) {
      console.error('Failed to update stage color:', err);
    }
  }

  async function handleStageTypeChange(stageId, stageType) {
    if (!onStageUpdate) return;
    try {
      await onStageUpdate(stageId, { stage_type: stageType });
    } catch (err) {
      console.error('Failed to update stage type:', err);
    }
  }

  // Drag-and-drop handlers
  function handleDragStart(index) {
    draggedIndex = index;
  }

  function handleDragOver(e, index) {
    e.preventDefault();
    dragOverIndex = index;
  }

  function handleDragLeave() {
    dragOverIndex = -1;
  }

  async function handleDrop(e, dropIndex) {
    e.preventDefault();
    dragOverIndex = -1;
    if (draggedIndex === -1 || draggedIndex === dropIndex || !onStageReorder) return;

    const reordered = [...sortedStages];
    const [moved] = reordered.splice(draggedIndex, 1);
    reordered.splice(dropIndex, 0, moved);

    const orderedIds = reordered.map((s) => s.id);
    draggedIndex = -1;

    try {
      await onStageReorder(pipeline.id, orderedIds);
    } catch (err) {
      console.error('Failed to reorder stages:', err);
    }
  }

  function handleDragEnd() {
    draggedIndex = -1;
    dragOverIndex = -1;
  }

  function toggleTeam(teamId) {
    const id = String(teamId);
    if (selectedTeams.has(id)) {
      selectedTeams.delete(id);
    } else {
      selectedTeams.add(id);
    }
    selectedTeams = new Set(selectedTeams);
  }

  function toggleUser(userId) {
    const id = String(userId);
    if (selectedUsers.has(id)) {
      selectedUsers.delete(id);
    } else {
      selectedUsers.add(id);
    }
    selectedUsers = new Set(selectedUsers);
  }

  const visibilityMode = $derived.by(() => {
    if (selectedTeams.size === 0 && selectedUsers.size === 0) return 'all';
    return 'restricted';
  });
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-lg max-h-[85vh] overflow-y-auto">
    <Dialog.Header>
      <Dialog.Title>Configurações — {pipeline?.name}</Dialog.Title>
      <Dialog.Description>
        Gerencie estágios, visibilidade e configurações do pipeline.
      </Dialog.Description>
    </Dialog.Header>

    <Tabs.Root bind:value={activeTab} class="mt-4">
      <Tabs.List class="w-full">
        <Tabs.Trigger value="stages" class="flex-1">Estágios</Tabs.Trigger>
        <Tabs.Trigger value="visibility" class="flex-1">Visibilidade</Tabs.Trigger>
        <Tabs.Trigger value="general" class="flex-1">Geral</Tabs.Trigger>
      </Tabs.List>

      <!-- Stages Tab -->
      <Tabs.Content value="stages" class="mt-4 space-y-3">
        <!-- Stage list -->
        {#each sortedStages as stage, index (stage.id)}
          <div
            class="flex items-center gap-2 rounded-lg border bg-white px-3 py-2 transition-colors dark:bg-gray-800
              {dragOverIndex === index && draggedIndex !== index
                ? 'border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/20'
                : 'border-gray-200 dark:border-gray-700'}
              {draggedIndex === index ? 'opacity-50' : ''}"
            draggable="true"
            ondragstart={() => handleDragStart(index)}
            ondragover={(e) => handleDragOver(e, index)}
            ondragleave={handleDragLeave}
            ondrop={(e) => handleDrop(e, index)}
            ondragend={handleDragEnd}
            role="listitem"
          >
            <GripVertical class="h-4 w-4 shrink-0 text-gray-400 cursor-grab" />

            <!-- Color dot -->
            <div class="relative">
              <input
                type="color"
                value={stage.color || '#6B7280'}
                class="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                onchange={(e) => handleStageColorChange(stage.id, e.target.value)}
              />
              <div
                class="h-4 w-4 shrink-0 rounded-full border border-gray-300 dark:border-gray-600"
                style="background-color: {stage.color || '#6B7280'}"
              ></div>
            </div>

            <!-- Stage name (editable via local state to avoid controlled input reset) -->
            <input
              type="text"
              value={editingStageNames[stage.id] ?? stage.name}
              class="flex-1 truncate border-0 bg-transparent px-1 py-0 text-sm font-medium text-gray-900 outline-none focus:ring-1 focus:ring-gray-300 rounded dark:text-gray-100 dark:focus:ring-gray-600"
              oninput={(e) => { editingStageNames[stage.id] = e.target.value; }}
              onblur={() => {
                const newName = (editingStageNames[stage.id] ?? stage.name).trim();
                delete editingStageNames[stage.id];
                editingStageNames = editingStageNames;
                if (newName && newName !== stage.name) {
                  handleStageNameChange(stage.id, newName, stage.name);
                }
              }}
              onkeydown={(e) => {
                if (e.key === 'Enter') {
                  e.target.blur();
                }
              }}
            />

            <!-- Stage type badge -->
            <select
              class="rounded border border-gray-200 bg-transparent px-1.5 py-0.5 text-xs font-medium dark:border-gray-600"
              value={stage.stage_type || 'open'}
              onchange={(e) => handleStageTypeChange(stage.id, e.target.value)}
            >
              {#each stageTypeOptions as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>

            <!-- Delete button -->
            <button
              type="button"
              class="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
              onclick={() => handleDeleteStage(stage.id)}
              title="Remover estágio"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        {/each}

        <!-- Add stage -->
        <div class="flex items-center gap-2">
          <Input
            bind:value={addingStageName}
            placeholder="Nome do novo estágio"
            class="flex-1 text-sm"
            onkeydown={(e) => e.key === 'Enter' && handleAddStage()}
          />
          <Button
            size="sm"
            variant="outline"
            onclick={handleAddStage}
            disabled={!addingStageName.trim() || addingStage}
          >
            {#if addingStage}
              <Loader2 class="h-4 w-4 animate-spin" />
            {:else}
              <Plus class="h-4 w-4" />
            {/if}
          </Button>
        </div>

        {#if stages.length === 0}
          <p class="py-4 text-center text-sm text-gray-500">
            Nenhum estágio definido. Adicione estágios acima.
          </p>
        {/if}
      </Tabs.Content>

      <!-- Visibility Tab -->
      <Tabs.Content value="visibility" class="mt-4 space-y-4">
        <div class="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/50">
          <div class="flex items-center gap-2 text-sm">
            {#if visibilityMode === 'all'}
              <Eye class="h-4 w-4 text-emerald-600" />
              <span class="font-medium text-emerald-700 dark:text-emerald-400">
                Visível para todos
              </span>
            {:else}
              <EyeOff class="h-4 w-4 text-amber-600" />
              <span class="font-medium text-amber-700 dark:text-amber-400">
                Restrito — {selectedTeams.size} times, {selectedUsers.size} usuários
              </span>
            {/if}
          </div>
          <p class="mt-1 text-xs text-gray-500">
            Se nenhum time ou usuário for selecionado, o pipeline será visível para todos.
          </p>
        </div>

        <!-- Teams -->
        {#if teams.length > 0}
          <div>
            <h4 class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              <Users class="h-4 w-4" />
              Times
            </h4>
            <div class="space-y-1.5 max-h-40 overflow-y-auto">
              {#each teams as team (team.id)}
                <label
                  class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-gray-100 dark:hover:bg-white/5 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedTeams.has(String(team.id))}
                    onchange={() => toggleTeam(team.id)}
                    class="rounded border-gray-300 text-gray-900 focus:ring-gray-500 dark:border-gray-600"
                  />
                  <span class="text-gray-700 dark:text-gray-300">{team.name}</span>
                </label>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Users -->
        {#if users.length > 0}
          <div>
            <h4 class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              <User class="h-4 w-4" />
              Usuários
            </h4>
            <div class="space-y-1.5 max-h-40 overflow-y-auto">
              {#each users as user (user.id)}
                <label
                  class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-gray-100 dark:hover:bg-white/5 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedUsers.has(String(user.id))}
                    onchange={() => toggleUser(user.id)}
                    class="rounded border-gray-300 text-gray-900 focus:ring-gray-500 dark:border-gray-600"
                  />
                  <span class="text-gray-700 dark:text-gray-300">
                    {user.name || user.email}
                  </span>
                </label>
              {/each}
            </div>
          </div>
        {/if}

        {#if teams.length === 0 && users.length === 0}
          <p class="py-4 text-center text-sm text-gray-500">
            Nenhum time ou usuário encontrado na organização.
          </p>
        {/if}
      </Tabs.Content>

      <!-- General Tab -->
      <Tabs.Content value="general" class="mt-4 space-y-4">
        <div>
          <label for="settings-name" class="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Nome
          </label>
          <Input id="settings-name" bind:value={pipelineName} />
        </div>

        <div>
          <label for="settings-desc" class="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Descrição
          </label>
          <textarea
            id="settings-desc"
            bind:value={pipelineDescription}
            rows="3"
            class="w-full rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-600"
          ></textarea>
        </div>

        <!-- Danger zone -->
        <div class="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800/50 dark:bg-red-900/10">
          <h4 class="text-sm font-medium text-red-800 dark:text-red-400">Zona de Perigo</h4>
          <p class="mt-1 text-xs text-red-600 dark:text-red-400/70">
            Excluir o pipeline removerá todos os estágios. Os itens perderão o estágio atual.
            {#if pipeline.is_default}Outro pipeline será promovido a padrão automaticamente.{/if}
          </p>
          <Button
            variant="destructive"
            size="sm"
            class="mt-2"
            onclick={() => {
              open = false;
              onConfirmDelete?.(pipeline.id);
            }}
          >
            <Trash2 class="mr-1.5 h-3.5 w-3.5" />
            Excluir Pipeline
          </Button>
        </div>
      </Tabs.Content>
    </Tabs.Root>

    <Dialog.Footer class="mt-4">
      <Button variant="outline" onclick={() => (open = false)}>
        Fechar
      </Button>
      <Button onclick={handleSavePipeline} disabled={saving}>
        {#if saving}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
        {/if}
        Salvar
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
