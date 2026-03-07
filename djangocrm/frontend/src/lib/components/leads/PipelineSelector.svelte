<script>
  import * as Select from '$lib/components/ui/select/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { GitBranch } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} pipelines
   * @property {string} [value] - Selected pipeline ID
   * @property {(pipelineId: string) => void} [onSelect]
   */

  /** @type {Props} */
  let { pipelines = [], value = '', onSelect } = $props();

  let selectedPipeline = $derived(pipelines.find(p => String(p.id) === String(value)));
</script>

<div class="flex items-center gap-3">
  <Select.Root type="single" {value} onValueChange={(v) => onSelect?.(v)}>
    <Select.Trigger class="w-56 gap-2">
      <GitBranch class="size-4 text-muted-foreground" />
      {selectedPipeline?.name || 'Selecionar pipeline...'}
    </Select.Trigger>
    <Select.Content>
      {#each pipelines as pipeline (pipeline.id)}
        <Select.Item value={String(pipeline.id)}>
          <span class="flex items-center gap-2">
            {pipeline.name}
            {#if pipeline.lead_count != null}
              <Badge variant="secondary" class="text-[10px] px-1.5">{pipeline.lead_count}</Badge>
            {/if}
          </span>
        </Select.Item>
      {/each}
      {#if pipelines.length === 0}
        <div class="px-2 py-4 text-center text-sm text-muted-foreground">
          Nenhum pipeline disponível
        </div>
      {/if}
    </Select.Content>
  </Select.Root>

  {#if selectedPipeline?.stages?.length}
    <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
      {#each selectedPipeline.stages as stage, i}
        {#if i > 0}<span class="opacity-40">→</span>{/if}
        <Badge variant="outline" class="text-[10px] px-1.5 py-0 {stage.wip_limit && stage.lead_count >= stage.wip_limit ? 'border-destructive text-destructive' : ''}">
          {stage.name}
          {#if stage.lead_count != null}({stage.lead_count}){/if}
        </Badge>
      {/each}
    </div>
  {/if}
</div>
