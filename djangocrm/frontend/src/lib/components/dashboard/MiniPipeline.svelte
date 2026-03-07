<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { ChevronRight } from '@lucide/svelte';
  import { formatCurrency } from '$lib/utils/formatting.js';

  /**
   * @typedef {Object} StageData
   * @property {number} count - Number of opportunities in this stage
   * @property {number} value - Total value of opportunities in this stage
   * @property {string} label - Display label for the stage
   */

  /**
   * @typedef {Object} Props
   * @property {Record<string, StageData>} [pipelineData] - Pipeline data by stage
   * @property {string} [currency] - Currency code for formatting (default: USD)
   */

  /** @type {Props} */
  let { pipelineData = {}, currency = 'USD' } = $props();

  // Closed stages are excluded from the active funnel view
  const CLOSED_STAGES = ['CLOSED_WON', 'CLOSED_LOST'];

  // Portuguese label overrides (API sends English labels)
  const STAGE_LABELS = /** @type {Record<string, string>} */ ({
    PROSPECTING: 'Prospecção',
    QUALIFICATION: 'Qualificação',
    PROPOSAL: 'Proposta',
    NEGOTIATION: 'Negociação'
  });

  // Style map for known stage IDs
  const STAGE_STYLES = /** @type {Record<string, { color: string, textColor: string, bgColor: string, borderColor: string, glowColor: string }>} */ ({
    PROSPECTING: {
      color: 'bg-[var(--stage-new)]',
      textColor: 'text-[var(--stage-new)]',
      bgColor: 'bg-orange-50/60 dark:bg-[var(--stage-new)]/15',
      borderColor: 'border-[var(--stage-new)]/30',
      glowColor: 'hover:shadow-[var(--stage-new)]/10'
    },
    QUALIFICATION: {
      color: 'bg-[var(--stage-qualified)]',
      textColor: 'text-[var(--stage-qualified)]',
      bgColor: 'bg-blue-50/60 dark:bg-[var(--stage-qualified)]/15',
      borderColor: 'border-[var(--stage-qualified)]/30',
      glowColor: 'hover:shadow-[var(--stage-qualified)]/10 dark:hover:shadow-[var(--stage-qualified)]/20'
    },
    PROPOSAL: {
      color: 'bg-[var(--stage-proposal)]',
      textColor: 'text-[var(--stage-proposal)]',
      bgColor: 'bg-violet-50/60 dark:bg-[var(--stage-proposal)]/15',
      borderColor: 'border-[var(--stage-proposal)]/30',
      glowColor: 'hover:shadow-[var(--stage-proposal)]/10 dark:hover:shadow-[var(--stage-proposal)]/20'
    },
    NEGOTIATION: {
      color: 'bg-[var(--stage-negotiation)]',
      textColor: 'text-[var(--stage-negotiation)]',
      bgColor: 'bg-amber-50/60 dark:bg-[var(--stage-negotiation)]/15',
      borderColor: 'border-[var(--stage-negotiation)]/30',
      glowColor: 'hover:shadow-[var(--stage-negotiation)]/10 dark:hover:shadow-[var(--stage-negotiation)]/20'
    }
  });

  // Fallback style for any unknown stage added in the future
  const DEFAULT_STYLE = {
    color: 'bg-[var(--color-primary-default)]',
    textColor: 'text-[var(--color-primary-default)]',
    bgColor: 'bg-orange-50/60 dark:bg-[var(--color-primary-default)]/15',
    borderColor: 'border-[var(--color-primary-default)]/30',
    glowColor: 'hover:shadow-[var(--color-primary-default)]/10'
  };

  // Derive active stages dynamically from pipelineData — order preserved from API
  const activeStages = $derived(
    Object.keys(pipelineData)
      .filter((id) => !CLOSED_STAGES.includes(id))
      .map((id) => ({ id, ...(STAGE_STYLES[id] || DEFAULT_STYLE) }))
  );
</script>

<div class="overflow-x-auto">
  <div class="flex min-w-max items-center gap-2">
    {#each activeStages as stage, index}
      {@const data = pipelineData[stage.id]}
      <a
        href="/opportunities?stage={stage.id}"
        class="group relative min-w-[130px] flex-1 overflow-hidden rounded-[var(--radius-lg)] border px-4 py-3.5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg backdrop-blur-md {stage.borderColor} {stage.bgColor} {stage.glowColor}"
      >
        <!-- Glass top-edge highlight -->
        <div
          class="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-[var(--radius-lg)] bg-gradient-to-r from-transparent via-white/80 to-transparent dark:via-white/10"
        ></div>

        <!-- White sheen overlay — always on, intensifies on hover -->
        <div
          class="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-white/[0.04]"
        ></div>

        <div class="relative flex flex-col gap-2">
          <!-- Stage header -->
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <div class="size-2.5 rounded-full {stage.color} shadow-sm"></div>
              <span class="text-xs font-semibold tracking-tight text-[var(--text-primary)]">
                {STAGE_LABELS[stage.id] || data.label || stage.id}
              </span>
            </div>
            <Badge
              variant="secondary"
              class="h-5 min-w-[1.5rem] justify-center px-1.5 text-[10px] font-bold {stage.textColor} {stage.bgColor} border {stage.borderColor}"
            >
              {data.count}
            </Badge>
          </div>

          <!-- Value -->
          <div class="flex items-center gap-2">
            <p class="text-lg font-bold tracking-tight text-[var(--text-primary)] tabular-nums">
              {formatCurrency(data.value, currency, true)}
            </p>
          </div>
        </div>
      </a>

      <!-- Connector arrows between stages -->
      {#if index < activeStages.length - 1}
        <div class="flex-shrink-0 px-1">
          <ChevronRight
            class="size-5 text-[var(--text-tertiary)]/30 transition-colors group-hover:text-[var(--text-tertiary)]/50"
          />
        </div>
      {/if}
    {/each}
  </div>
</div>
