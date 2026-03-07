<script>
  import { cn } from '$lib/utils.js';
  import { TrendingUp, TrendingDown } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} label - The metric label (e.g., "Active Leads")
   * @property {string | number} value - The metric value
   * @property {string} [subtitle] - Small note below the value (e.g., "INR only")
   * @property {import('svelte').Snippet} [icon] - Icon snippet to display
   * @property {number} [trend] - Percentage change (positive or negative)
   * @property {string} [trendLabel] - Label for trend (e.g., "vs last month")
   * @property {'orange' | 'cyan' | 'violet' | 'emerald' | 'amber' | 'rose' | 'blue'} [accentColor] - Accent color theme
   * @property {string} [class] - Additional classes
   */

  /** @type {Props & Record<string, any>} */
  let {
    label,
    value,
    subtitle,
    icon,
    trend,
    trendLabel,
    accentColor = 'orange',
    class: className,
    ...restProps
  } = $props();

  const hasTrend = $derived(trend !== undefined && trend !== null);
  const isPositive = $derived(trend !== undefined && trend >= 0);

  // Color configurations using design system tokens
  // cardBg: semi-transparent accent tint so backdrop-blur is visibly "glassy"
  const colorConfig = {
    orange: {
      cardBg: 'bg-orange-50/60 dark:bg-[var(--color-primary-default)]/10',
      iconBg: 'bg-[var(--color-primary-light)] dark:bg-[var(--color-primary-default)]/15',
      iconColor: 'text-[var(--color-primary-default)] dark:text-[var(--color-primary-default)]',
      borderGlow: 'hover:border-[var(--color-primary-default)]/30',
      shadowGlow: 'dark:hover:shadow-[var(--color-primary-default)]/10'
    },
    cyan: {
      cardBg: 'bg-cyan-50/60 dark:bg-cyan-500/10',
      iconBg: 'bg-cyan-500/10 dark:bg-cyan-500/20',
      iconColor: 'text-cyan-600 dark:text-cyan-400',
      borderGlow: 'hover:border-cyan-500/30 dark:hover:border-cyan-400/30',
      shadowGlow: 'dark:hover:shadow-cyan-500/10'
    },
    violet: {
      cardBg: 'bg-violet-50/60 dark:bg-[var(--stage-proposal)]/10',
      iconBg: 'bg-[var(--stage-proposal-bg)] dark:bg-[var(--stage-proposal)]/15',
      iconColor: 'text-[var(--stage-proposal)] dark:text-[var(--stage-proposal)]',
      borderGlow: 'hover:border-[var(--stage-proposal)]/30',
      shadowGlow: 'dark:hover:shadow-[var(--stage-proposal)]/10'
    },
    blue: {
      cardBg: 'bg-blue-50/60 dark:bg-[var(--stage-qualified)]/10',
      iconBg: 'bg-[var(--stage-qualified-bg)] dark:bg-[var(--stage-qualified)]/15',
      iconColor: 'text-[var(--stage-qualified)] dark:text-[var(--stage-qualified)]',
      borderGlow: 'hover:border-[var(--stage-qualified)]/30',
      shadowGlow: 'dark:hover:shadow-[var(--stage-qualified)]/10'
    },
    emerald: {
      cardBg: 'bg-emerald-50/60 dark:bg-[var(--stage-won)]/10',
      iconBg: 'bg-[var(--color-success-light)] dark:bg-[var(--stage-won)]/15',
      iconColor: 'text-[var(--stage-won)] dark:text-[var(--stage-won)]',
      borderGlow: 'hover:border-[var(--stage-won)]/30',
      shadowGlow: 'dark:hover:shadow-[var(--stage-won)]/10'
    },
    amber: {
      cardBg: 'bg-amber-50/60 dark:bg-[var(--stage-negotiation)]/10',
      iconBg: 'bg-[var(--stage-negotiation-bg)] dark:bg-[var(--stage-negotiation)]/15',
      iconColor: 'text-[var(--stage-negotiation)] dark:text-[var(--stage-negotiation)]',
      borderGlow: 'hover:border-[var(--stage-negotiation)]/30',
      shadowGlow: 'dark:hover:shadow-[var(--stage-negotiation)]/10'
    },
    rose: {
      cardBg: 'bg-rose-50/60 dark:bg-[var(--stage-lost)]/10',
      iconBg: 'bg-[var(--stage-lost-bg)] dark:bg-[var(--stage-lost)]/15',
      iconColor: 'text-[var(--stage-lost)] dark:text-[var(--stage-lost)]',
      borderGlow: 'hover:border-[var(--stage-lost)]/30',
      shadowGlow: 'dark:hover:shadow-[var(--stage-lost)]/10'
    }
  };

  const colors = $derived(colorConfig[accentColor] || colorConfig.orange);
</script>

<div
  class={cn(
    'group relative overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] p-5 transition-all duration-300',
    'backdrop-blur-md hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]',
    'dark:border-[var(--border-default)] dark:hover:shadow-lg',
    colors.cardBg,
    colors.borderGlow,
    colors.shadowGlow,
    className
  )}
  {...restProps}
>
  <!-- Glass top-edge highlight (simulates light hitting glass) -->
  <div
    class="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-[var(--radius-lg)] bg-gradient-to-r from-transparent via-white/80 to-transparent dark:via-white/10"
  ></div>

  <!-- Accent gradient overlay — subtle always-on tint + stronger on hover -->
  <div
    class="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-white/[0.03] dark:to-transparent"
  ></div>

  <div class="relative flex items-start justify-between gap-4">
    <div class="flex min-w-0 flex-col gap-1.5">
      <!-- Label -->
      <p class="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">
        {label}
      </p>

      <!-- Value -->
      <p
        class="truncate text-2xl font-bold tracking-tight text-[var(--text-primary)] tabular-nums lg:text-3xl"
      >
        {value}
      </p>

      <!-- Subtitle -->
      {#if subtitle}
        <p class="text-[10px] font-medium text-[var(--text-tertiary)]">{subtitle}</p>
      {/if}

      <!-- Trend indicator -->
      {#if hasTrend}
        <div class="mt-1 flex items-center gap-1.5">
          {#if isPositive}
            <div
              class="flex items-center gap-1 rounded-full bg-[var(--color-success-light)] px-2 py-0.5 dark:bg-[var(--stage-won)]/15"
            >
              <TrendingUp class="size-3 text-[var(--stage-won)]" />
              <span class="text-xs font-semibold text-[var(--stage-won)]">
                +{trend}%
              </span>
            </div>
          {:else}
            <div
              class="flex items-center gap-1 rounded-full bg-[var(--stage-lost-bg)] px-2 py-0.5 dark:bg-[var(--stage-lost)]/15"
            >
              <TrendingDown class="size-3 text-[var(--stage-lost)]" />
              <span class="text-xs font-semibold text-[var(--stage-lost)]">
                {trend}%
              </span>
            </div>
          {/if}
          {#if trendLabel}
            <span class="text-[10px] text-[var(--text-tertiary)]">{trendLabel}</span>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Icon -->
    {#if icon}
      <div
        class={cn(
          'flex size-11 flex-shrink-0 items-center justify-center rounded-[var(--radius-lg)] transition-transform duration-300 group-hover:scale-105',
          colors.iconBg
        )}
      >
        <div class={colors.iconColor}>
          {@render icon()}
        </div>
      </div>
    {/if}
  </div>
</div>
