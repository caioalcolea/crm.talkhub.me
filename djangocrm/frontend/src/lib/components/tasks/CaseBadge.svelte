<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Briefcase } from '@lucide/svelte';

  /**
   * Badge visual indicando que task originou-se de um case.
   *
   * @typedef {Object} Props
   * @property {string} caseId
   * @property {string} [caseTitle]
   */

  /** @type {Props} */
  let { caseId = '', caseTitle = '' } = $props();
</script>

{#if caseId}
  <a href="/cases/{caseId}" class="inline-flex">
    <Badge variant="outline" class="gap-1 px-1.5 py-0 text-[10px] hover:bg-muted transition-colors cursor-pointer border-blue-200 text-blue-700 dark:border-blue-800 dark:text-blue-400">
      <Briefcase class="size-2.5" />
      {caseTitle || 'Chamado'}
    </Badge>
  </a>
{/if}
