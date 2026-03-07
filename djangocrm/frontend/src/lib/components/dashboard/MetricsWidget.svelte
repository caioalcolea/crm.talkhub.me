<script>
  import * as Card from '$lib/components/ui/card/index.js';
  import { Bot, MessageSquare, Clock, CheckCircle, TrendingUp, TrendingDown } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} title
   * @property {string|number} value
   * @property {string} [icon] - 'bot' | 'message' | 'clock' | 'check'
   * @property {number} [change] - Percentage change
   * @property {string} [suffix]
   */

  /** @type {Props} */
  let { title = '', value = 0, icon = 'message', change, suffix = '' } = $props();


</script>

<Card.Root>
  <Card.Content class="p-4">
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-muted-foreground">{title}</span>
      {#if icon === 'bot'}
        <Bot class="size-4 text-muted-foreground" />
      {:else if icon === 'clock'}
        <Clock class="size-4 text-muted-foreground" />
      {:else if icon === 'check'}
        <CheckCircle class="size-4 text-muted-foreground" />
      {:else}
        <MessageSquare class="size-4 text-muted-foreground" />
      {/if}
    </div>
    <div class="mt-2 flex items-baseline gap-1">
      <span class="text-2xl font-bold">{value}</span>
      {#if suffix}
        <span class="text-sm text-muted-foreground">{suffix}</span>
      {/if}
    </div>
    {#if change != null}
      <div class="mt-1 flex items-center gap-1 text-xs {change >= 0 ? 'text-emerald-600' : 'text-red-600'}">
        {#if change >= 0}
          <TrendingUp class="size-3" />
        {:else}
          <TrendingDown class="size-3" />
        {/if}
        {change > 0 ? '+' : ''}{change}%
      </div>
    {/if}
  </Card.Content>
</Card.Root>
