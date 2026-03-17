<script>
  import { Plus, Settings, Trash2, Loader2 } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import PipelineSettingsDialog from './PipelineSettingsDialog.svelte';

  /**
   * @typedef {Object} Pipeline
   * @property {string} id
   * @property {string} name
   * @property {boolean} is_default
   * @property {number} [stage_count]
   * @property {number} [opportunity_count]
   * @property {Array} [stages]
   * @property {Array} [visible_to_teams]
   * @property {Array} [visible_to_users]
   */

  /**
   * @type {{
   *   pipelines: Pipeline[],
   *   activePipelineId?: string,
   *   onSelect: (id: string) => void,
   *   onCreate?: (data: {name: string, create_default_stages: boolean}) => Promise<any>,
   *   onDelete?: (id: string) => Promise<void>,
   *   onUpdate?: (id: string, data: any) => Promise<void>,
   *   onStageCreate?: (pipelineId: string, data: any) => Promise<any>,
   *   onStageUpdate?: (stageId: string, data: any) => Promise<void>,
   *   onStageDelete?: (stageId: string) => Promise<void>,
   *   onStageReorder?: (pipelineId: string, order: string[]) => Promise<void>,
   *   canManage?: boolean,
   *   teams?: Array<{id: string, name: string}>,
   *   users?: Array<{id: string, name: string, email?: string}>,
   *   module?: string
   * }}
   */
  let {
    pipelines = [],
    activePipelineId = '',
    onSelect,
    onCreate,
    onDelete,
    onUpdate,
    onStageCreate,
    onStageUpdate,
    onStageDelete,
    onStageReorder,
    canManage = false,
    teams = [],
    users = [],
    module = 'leads'
  } = $props();

  // Create dialog state
  let createDialogOpen = $state(false);
  let newPipelineName = $state('');
  let createDefaultStages = $state(true);
  let creating = $state(false);

  // Settings dialog state
  let settingsDialogOpen = $state(false);
  let settingsPipeline = $state(null);

  // Delete confirmation state
  let deleteDialogOpen = $state(false);
  let deletingPipelineId = $state('');
  let deleting = $state(false);

  const activePipeline = $derived(
    pipelines.find((p) => p.id === activePipelineId) || null
  );

  // Keep settings dialog in sync when pipelines data refreshes (after invalidateAll)
  $effect(() => {
    if (settingsDialogOpen && settingsPipeline) {
      const fresh = pipelines.find((p) => p.id === settingsPipeline.id);
      if (fresh) settingsPipeline = fresh;
    }
  });

  async function handleCreate() {
    if (!newPipelineName.trim() || !onCreate) return;
    creating = true;
    try {
      await onCreate({
        name: newPipelineName.trim(),
        create_default_stages: createDefaultStages
      });
      newPipelineName = '';
      createDefaultStages = true;
      createDialogOpen = false;
    } catch (err) {
      console.error('Failed to create pipeline:', err);
    } finally {
      creating = false;
    }
  }

  function openSettings(pipeline) {
    settingsPipeline = pipeline;
    settingsDialogOpen = true;
  }

  function confirmDelete(pipelineId) {
    deletingPipelineId = pipelineId;
    deleteDialogOpen = true;
  }

  async function handleDelete() {
    if (!deletingPipelineId || !onDelete) return;
    deleting = true;
    try {
      await onDelete(deletingPipelineId);
      if (activePipelineId === deletingPipelineId) {
        onSelect('');
      }
      deleteDialogOpen = false;
      deletingPipelineId = '';
    } catch (err) {
      console.error('Failed to delete pipeline:', err);
    } finally {
      deleting = false;
    }
  }
</script>

{#if pipelines.length > 0 || canManage}
<div class="flex items-center gap-2 overflow-x-auto pb-1">
  <!-- Default (status-based) tab -->
  <button
    type="button"
    class="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-all
      {!activePipelineId
        ? 'bg-gray-900 text-white shadow-sm dark:bg-white dark:text-gray-900'
        : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10'}"
    onclick={() => onSelect('')}
  >
    Padrão
  </button>

  <!-- Pipeline tabs -->
  {#each pipelines as pipeline (pipeline.id)}
    <div class="group relative flex shrink-0 items-center">
      <button
        type="button"
        class="rounded-lg px-3 py-1.5 text-sm font-medium transition-all
          {activePipelineId === pipeline.id
            ? 'bg-gray-900 text-white shadow-sm dark:bg-white dark:text-gray-900'
            : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10'}"
        onclick={() => onSelect(pipeline.id)}
      >
        {pipeline.name}
        {#if pipeline.stage_count != null}
          <span class="ml-1 text-xs opacity-60">({pipeline.stage_count})</span>
        {/if}
      </button>

      <!-- Settings gear (visible on hover for active pipeline) -->
      {#if canManage && activePipelineId === pipeline.id}
        <button
          type="button"
          class="ml-0.5 rounded-md p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-white/10 dark:hover:text-gray-300"
          onclick={() => openSettings(pipeline)}
          title="Configurações do pipeline"
        >
          <Settings class="h-3.5 w-3.5" />
        </button>
      {/if}
    </div>
  {/each}

  <!-- Create pipeline button -->
  {#if canManage}
    <button
      type="button"
      class="shrink-0 rounded-lg border border-dashed border-gray-300 px-2 py-1.5 text-sm text-gray-500 transition-all hover:border-gray-400 hover:bg-gray-50 hover:text-gray-700 dark:border-gray-600 dark:text-gray-400 dark:hover:border-gray-500 dark:hover:bg-white/5 dark:hover:text-gray-300"
      onclick={() => (createDialogOpen = true)}
      title="Criar novo pipeline"
    >
      <Plus class="h-4 w-4" />
    </button>
  {/if}
</div>
{/if}

<!-- Create Pipeline Dialog -->
<Dialog.Root bind:open={createDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Novo Pipeline</Dialog.Title>
      <Dialog.Description>
        Crie um novo pipeline com estágios personalizados.
      </Dialog.Description>
    </Dialog.Header>

    <div class="space-y-4 py-4">
      <div>
        <label for="pipeline-name" class="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
          Nome do Pipeline
        </label>
        <Input
          id="pipeline-name"
          bind:value={newPipelineName}
          placeholder="Ex: Pipeline Corporativo"
          onkeydown={(e) => e.key === 'Enter' && handleCreate()}
        />
      </div>

      <label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
        <input
          type="checkbox"
          bind:checked={createDefaultStages}
          class="rounded border-gray-300 text-gray-900 focus:ring-gray-500 dark:border-gray-600"
        />
        Criar estágios padrão
      </label>
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (createDialogOpen = false)}>
        Cancelar
      </Button>
      <Button onclick={handleCreate} disabled={!newPipelineName.trim() || creating}>
        {#if creating}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
        {/if}
        Criar
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- Delete Confirmation Dialog -->
<Dialog.Root bind:open={deleteDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Excluir Pipeline</Dialog.Title>
      <Dialog.Description>
        Tem certeza? Os itens neste pipeline voltarão para o modo padrão. Esta ação não pode ser desfeita.
      </Dialog.Description>
    </Dialog.Header>
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (deleteDialogOpen = false)}>
        Cancelar
      </Button>
      <Button variant="destructive" onclick={handleDelete} disabled={deleting}>
        {#if deleting}
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
        {/if}
        Excluir
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- Pipeline Settings Dialog -->
{#if settingsDialogOpen && settingsPipeline}
  <PipelineSettingsDialog
    pipeline={settingsPipeline}
    {teams}
    {users}
    {module}
    bind:open={settingsDialogOpen}
    {onUpdate}
    {onDelete}
    {onStageCreate}
    {onStageUpdate}
    {onStageDelete}
    {onStageReorder}
    onConfirmDelete={confirmDelete}
  />
{/if}
