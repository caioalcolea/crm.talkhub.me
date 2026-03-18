<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Plus, CheckSquare, Clock, User } from '@lucide/svelte';
  import { safeParseDateOnly } from '$lib/utils/formatting.js';

  /**
   * @typedef {Object} Props
   * @property {any[]} tasks
   * @property {string} caseId
   * @property {() => void} [onCreateTask]
   */

  /** @type {Props} */
  let { tasks = [], caseId = '', onCreateTask } = $props();

  const statusLabels = {
    todo: 'A fazer',
    in_progress: 'Em andamento',
    done: 'Concluída',
    cancelled: 'Cancelada'
  };

  const statusColors = {
    todo: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    done: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    cancelled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
  };

  /** @param {string} dateStr */
  function formatDate(dateStr) {
    if (!dateStr) return '';
    return safeParseDateOnly(dateStr).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  }
</script>

<div class="space-y-3">
  <div class="flex items-center justify-between">
    <h4 class="text-sm font-medium flex items-center gap-1.5">
      <CheckSquare class="size-4" />
      Tarefas ({tasks.length})
    </h4>
    <Button variant="outline" size="sm" class="gap-1.5 h-7 text-xs" onclick={() => onCreateTask?.()}>
      <Plus class="size-3.5" />
      Nova Tarefa
    </Button>
  </div>

  {#if tasks.length === 0}
    <p class="text-xs text-muted-foreground py-4 text-center">Nenhuma tarefa vinculada</p>
  {:else}
    <div class="divide-y rounded-lg border">
      {#each tasks as task (task.id)}
        <a href="/tasks/{task.id}" class="flex items-center gap-3 px-3 py-2 hover:bg-muted/50 transition-colors">
          <div class="flex-1 min-w-0">
            <p class="text-sm truncate">{task.title}</p>
            <div class="flex items-center gap-2 mt-0.5">
              <Badge variant="outline" class="text-[10px] px-1.5 py-0 {statusColors[task.status] || ''}">
                {statusLabels[task.status] || task.status}
              </Badge>
              {#if task.assigned_to_name}
                <span class="text-[10px] text-muted-foreground flex items-center gap-1">
                  <User class="size-2.5" />
                  {task.assigned_to_name}
                </span>
              {/if}
            </div>
          </div>
          {#if task.due_date}
            <span class="text-[10px] text-muted-foreground flex items-center gap-1 shrink-0">
              <Clock class="size-3" />
              {formatDate(task.due_date)}
            </span>
          {/if}
        </a>
      {/each}
    </div>
  {/if}
</div>
