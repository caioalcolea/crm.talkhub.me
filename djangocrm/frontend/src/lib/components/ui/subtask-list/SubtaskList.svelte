<script>
  import { CheckSquare, Square, Plus, X, GripVertical, Trash2 } from '@lucide/svelte';
  import { cn } from '$lib/utils.js';

  /**
   * @typedef {Object} Subtask
   * @property {string} id
   * @property {string} title
   * @property {boolean} is_completed
   * @property {number} order
   */

  /**
   * Reusable subtask/checklist component for Tasks and Cases drawers.
   * @type {{
   *   subtasks?: Subtask[],
   *   onAdd?: (title: string) => Promise<void>,
   *   onToggle?: (id: string, completed: boolean) => Promise<void>,
   *   onUpdate?: (id: string, title: string) => Promise<void>,
   *   onDelete?: (id: string) => Promise<void>,
   *   onReorder?: (orderedIds: string[]) => Promise<void>,
   *   readonly?: boolean
   * }}
   */
  let {
    subtasks = [],
    onAdd,
    onToggle,
    onUpdate,
    onDelete,
    onReorder,
    readonly = false
  } = $props();

  let newItemText = $state('');
  let isAdding = $state(false);
  let editingId = $state(null);
  let editingText = $state('');
  let dragOverId = $state(null);
  let draggedId = $state(null);

  const completed = $derived(subtasks.filter((s) => s.is_completed).length);
  const total = $derived(subtasks.length);
  const progress = $derived(total > 0 ? Math.round((completed / total) * 100) : 0);

  async function handleAdd() {
    const text = newItemText.trim();
    if (!text || !onAdd) return;
    await onAdd(text);
    newItemText = '';
  }

  function handleAddKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    } else if (e.key === 'Escape') {
      isAdding = false;
      newItemText = '';
    }
  }

  async function handleToggle(subtask) {
    if (!onToggle || readonly) return;
    await onToggle(subtask.id, !subtask.is_completed);
  }

  function startEditing(subtask) {
    if (readonly) return;
    editingId = subtask.id;
    editingText = subtask.title;
  }

  async function finishEditing() {
    if (!editingId || !onUpdate) return;
    const text = editingText.trim();
    if (text && text !== subtasks.find((s) => s.id === editingId)?.title) {
      await onUpdate(editingId, text);
    }
    editingId = null;
    editingText = '';
  }

  function handleEditKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      finishEditing();
    } else if (e.key === 'Escape') {
      editingId = null;
      editingText = '';
    }
  }

  // Drag and drop
  function handleDragStart(e, subtask) {
    if (readonly) return;
    draggedId = subtask.id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', subtask.id);
  }

  function handleDragOver(e, subtask) {
    e.preventDefault();
    if (draggedId && draggedId !== subtask.id) {
      dragOverId = subtask.id;
    }
  }

  function handleDragLeave() {
    dragOverId = null;
  }

  async function handleDrop(e, targetSubtask) {
    e.preventDefault();
    dragOverId = null;
    if (!draggedId || draggedId === targetSubtask.id || !onReorder) return;

    const ordered = [...subtasks];
    const dragIdx = ordered.findIndex((s) => s.id === draggedId);
    const targetIdx = ordered.findIndex((s) => s.id === targetSubtask.id);
    if (dragIdx === -1 || targetIdx === -1) return;

    const [item] = ordered.splice(dragIdx, 1);
    ordered.splice(targetIdx, 0, item);
    await onReorder(ordered.map((s) => s.id));
    draggedId = null;
  }

  function handleDragEnd() {
    draggedId = null;
    dragOverId = null;
  }
</script>

<div class="subtask-list">
  <!-- Progress bar -->
  {#if total > 0}
    <div class="mb-3 flex items-center gap-2">
      <div class="text-muted-foreground flex items-center gap-1.5 text-xs font-medium">
        <CheckSquare class="h-3.5 w-3.5" />
        <span>{completed}/{total}</span>
      </div>
      <div class="bg-muted h-1.5 flex-1 overflow-hidden rounded-full">
        <div
          class="h-full rounded-full transition-all duration-300 {progress === 100
            ? 'bg-emerald-500'
            : 'bg-primary'}"
          style="width: {progress}%"
        ></div>
      </div>
    </div>
  {/if}

  <!-- Subtask items -->
  <div class="space-y-0.5">
    {#each subtasks as subtask (subtask.id)}
      <div
        class={cn(
          'group flex items-center gap-1.5 rounded-md px-1 py-1 transition-colors',
          dragOverId === subtask.id && 'bg-primary/10 border-primary/30 border',
          draggedId === subtask.id && 'opacity-40'
        )}
        ondragover={(e) => handleDragOver(e, subtask)}
        ondragleave={handleDragLeave}
        ondrop={(e) => handleDrop(e, subtask)}
      >
        <!-- Drag handle -->
        {#if !readonly}
          <div
            class="text-muted-foreground/30 cursor-grab opacity-0 transition-opacity group-hover:opacity-100"
            draggable="true"
            ondragstart={(e) => handleDragStart(e, subtask)}
            ondragend={handleDragEnd}
            role="presentation"
          >
            <GripVertical class="h-3.5 w-3.5" />
          </div>
        {/if}

        <!-- Checkbox -->
        <button
          class="shrink-0 transition-colors"
          onclick={() => handleToggle(subtask)}
          disabled={readonly}
        >
          {#if subtask.is_completed}
            <CheckSquare class="h-4 w-4 text-emerald-500" />
          {:else}
            <Square class="text-muted-foreground/50 hover:text-foreground h-4 w-4" />
          {/if}
        </button>

        <!-- Title -->
        {#if editingId === subtask.id}
          <input
            type="text"
            bind:value={editingText}
            onblur={finishEditing}
            onkeydown={handleEditKeydown}
            class="text-foreground min-w-0 flex-1 border-none bg-transparent text-sm outline-none"
            autofocus
          />
        {:else}
          <button
            class={cn(
              'min-w-0 flex-1 truncate text-left text-sm transition-colors',
              subtask.is_completed
                ? 'text-muted-foreground line-through'
                : 'text-foreground'
            )}
            ondblclick={() => startEditing(subtask)}
            disabled={readonly}
          >
            {subtask.title}
          </button>
        {/if}

        <!-- Delete button -->
        {#if !readonly}
          <button
            class="text-muted-foreground/30 hover:text-destructive shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
            onclick={() => onDelete?.(subtask.id)}
            title="Remover"
          >
            <Trash2 class="h-3.5 w-3.5" />
          </button>
        {/if}
      </div>
    {/each}
  </div>

  <!-- Add new item -->
  {#if !readonly}
    {#if isAdding}
      <div class="mt-1.5 flex items-center gap-1.5 px-1">
        <Square class="text-muted-foreground/30 h-4 w-4 shrink-0" />
        <input
          type="text"
          bind:value={newItemText}
          onkeydown={handleAddKeydown}
          onblur={() => {
            if (!newItemText.trim()) isAdding = false;
          }}
          placeholder="Novo item..."
          class="text-foreground placeholder:text-muted-foreground/50 min-w-0 flex-1 border-none bg-transparent text-sm outline-none"
          autofocus
        />
        <button
          class="text-muted-foreground hover:text-foreground shrink-0"
          onclick={() => {
            isAdding = false;
            newItemText = '';
          }}
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>
    {:else}
      <button
        class="text-muted-foreground hover:text-foreground mt-1.5 flex items-center gap-1.5 px-1 text-sm transition-colors"
        onclick={() => (isAdding = true)}
      >
        <Plus class="h-3.5 w-3.5" />
        <span>Adicionar item</span>
      </button>
    {/if}
  {/if}
</div>
