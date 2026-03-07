<script>
  import * as Select from '$lib/components/ui/select/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Layers } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} ticketLists
   * @property {(listId: string, mapping: string) => void} [onMap]
   */

  /** @type {Props} */
  let { ticketLists = [], onMap } = $props();

  const mappingOptions = [
    { value: 'sales_pipeline', label: 'Funil de Vendas' },
    { value: 'support', label: 'Suporte' },
    { value: 'none', label: 'Não mapear' },
  ];
</script>

<div class="space-y-2">
  {#each ticketLists as list (list.id)}
    <div class="flex items-center gap-3 rounded-lg bg-muted/50 px-3 py-2">
      <Layers class="size-4 text-muted-foreground shrink-0" />
      <span class="flex-1 text-sm font-medium truncate">{list.name}</span>
      <Select.Root type="single" value={list.mapping || 'none'} onValueChange={(v) => onMap?.(list.id, v)}>
        <Select.Trigger class="w-40 h-8 text-xs">
          {mappingOptions.find(o => o.value === (list.mapping || 'none'))?.label || 'Selecione...'}
        </Select.Trigger>
        <Select.Content>
          {#each mappingOptions as opt}
            <Select.Item value={opt.value}>{opt.label}</Select.Item>
          {/each}
        </Select.Content>
      </Select.Root>
    </div>
  {:else}
    <p class="text-muted-foreground text-sm text-center py-4">Nenhuma ticket list encontrada.</p>
  {/each}
</div>
