<script>
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Trophy, User } from '@lucide/svelte';

  /**
   * @typedef {Object} Agent
   * @property {string} name
   * @property {number} conversations_resolved
   * @property {number} [avg_response_min]
   * @property {number} [satisfaction_score]
   *
   * @typedef {Object} Props
   * @property {Agent[]} agents
   */

  /** @type {Props} */
  let { agents = [] } = $props();
</script>

<Card.Root>
  <Card.Header class="pb-3">
    <Card.Title class="flex items-center gap-2 text-sm">
      <Trophy class="size-4" />
      Top Agentes
    </Card.Title>
  </Card.Header>
  <Card.Content>
    {#if agents.length === 0}
      <p class="text-xs text-muted-foreground py-4 text-center">Sem dados de produtividade</p>
    {:else}
      <div class="divide-y">
        {#each agents as agent, i}
          <div class="flex items-center gap-3 py-2">
            <span class="text-xs font-bold text-muted-foreground w-5">{i + 1}.</span>
            <div class="flex size-7 items-center justify-center rounded-full bg-muted">
              <User class="size-3.5 text-muted-foreground" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm truncate">{agent.name}</p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <Badge variant="secondary" class="text-[10px]">{agent.conversations_resolved} resolvidas</Badge>
              {#if agent.avg_response_min != null}
                <span class="text-[10px] text-muted-foreground">{agent.avg_response_min}min</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </Card.Content>
</Card.Root>
