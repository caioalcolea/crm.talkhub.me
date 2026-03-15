<script>
  import { useSidebar } from '$lib/components/ui/sidebar/context.svelte.js';
  import { Menu } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} title - Page title
   * @property {string} [subtitle] - Optional subtitle
   * @property {import('svelte').Snippet} [actions] - Optional actions snippet
   */

  /** @type {Props} */
  let { title, subtitle = '', actions } = $props();

  const sidebar = useSidebar();
</script>

<header
  class="border-border/40 from-background via-background to-background/95 supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10 border-b bg-gradient-to-r backdrop-blur-2xl"
>
  <!-- Ambient glow effect for dark mode -->
  <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
    <div
      class="bg-primary/5 dark:bg-primary/10 absolute -top-24 left-1/4 h-48 w-96 rounded-full blur-3xl"
    ></div>
    <div
      class="bg-accent/5 absolute -top-24 right-1/4 h-48 w-64 rounded-full blur-3xl dark:bg-cyan-500/8"
    ></div>
  </div>

  <div class="relative flex min-h-[3.5rem] items-center justify-between gap-3 px-4 py-3 md:min-h-[4.5rem] md:gap-6 md:px-8 md:py-4">
    <!-- Mobile menu button -->
    <button
      onclick={() => sidebar.setOpenMobile(true)}
      class="text-muted-foreground hover:text-foreground hover:bg-accent -ml-1 flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors md:hidden"
      aria-label="Abrir menu"
    >
      <Menu class="size-5" />
    </button>

    <!-- Title Section -->
    <div class="flex min-w-0 flex-1 flex-col gap-1">
      <div class="flex items-baseline gap-3">
        <h1
          class="text-foreground truncate text-xl font-bold tracking-tight md:text-[1.75rem]"
          style="letter-spacing: -0.025em;"
        >
          {title}
        </h1>
        {#if subtitle}
          <span class="hidden items-center gap-2 sm:flex">
            <span class="bg-muted-foreground/30 h-1 w-1 rounded-full"></span>
            <p class="text-muted-foreground/80 text-sm font-medium">{subtitle}</p>
          </span>
        {/if}
      </div>
      {#if subtitle}
        <p class="text-muted-foreground/80 text-sm font-medium sm:hidden">{subtitle}</p>
      {/if}
    </div>

    <!-- Actions Section -->
    {#if actions}
      <div class="flex shrink-0 items-center gap-2 md:gap-3">
        {@render actions()}
      </div>
    {/if}
  </div>

  <!-- Bottom accent line -->
  <div
    class="via-border/60 absolute right-0 bottom-0 left-0 h-px bg-gradient-to-r from-transparent to-transparent"
  ></div>
</header>
