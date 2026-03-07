<script>
  /**
   * Icon wrapper that applies strokeWidth={1.5} by default to any Lucide icon.
   *
   * Usage:
   *   import Icon from '$lib/components/ui/icon.svelte';
   *   import ChevronRight from '@lucide/svelte/icons/chevron-right';
   *
   *   <Icon icon={ChevronRight} class="h-4 w-4" />
   *   <Icon icon={ChevronRight} strokeWidth={1} class="h-5 w-5" />
   *
   * @type {{
   *   icon: import('svelte').Component,
   *   strokeWidth?: number,
   *   class?: string,
   *   [key: string]: any
   * }}
   */
  let {
    icon: IconComponent,
    strokeWidth = 1.5,
    class: className = '',
    ...restProps
  } = $props();
</script>

<IconComponent {strokeWidth} class={className} {...restProps} />
