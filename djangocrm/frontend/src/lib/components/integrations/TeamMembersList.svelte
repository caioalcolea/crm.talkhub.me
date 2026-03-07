<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { User, Users } from '@lucide/svelte';

  /**
   * Lista de membros da equipe sincronizados com indicador online/offline.
   *
   * @typedef {Object} TeamMember
   * @property {string} id
   * @property {string} name
   * @property {string} [email]
   * @property {string} [role]
   * @property {boolean} [is_online]
   * @property {string} [avatar]
   *
   * @typedef {Object} Props
   * @property {TeamMember[]} members
   */

  /** @type {Props} */
  let { members = [] } = $props();

  let onlineCount = $derived(members.filter(m => m.is_online).length);
</script>

<div class="space-y-3">
  <div class="flex items-center justify-between">
    <h4 class="text-sm font-medium flex items-center gap-1.5">
      <Users class="size-4" />
      Equipe ({members.length})
    </h4>
    <Badge variant="outline" class="text-[10px] gap-1 border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-400">
      {onlineCount} online
    </Badge>
  </div>

  {#if members.length === 0}
    <p class="text-xs text-muted-foreground py-4 text-center">Nenhum membro sincronizado</p>
  {:else}
    <div class="divide-y rounded-lg border">
      {#each members as member (member.id)}
        <div class="flex items-center gap-3 px-3 py-2">
          <div class="relative">
            {#if member.avatar}
              <img src={member.avatar} alt={member.name} class="size-8 rounded-full object-cover" />
            {:else}
              <div class="flex size-8 items-center justify-center rounded-full bg-muted">
                <User class="size-4 text-muted-foreground" />
              </div>
            {/if}
            <div class="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full border-2 border-background {member.is_online ? 'bg-emerald-500' : 'bg-gray-400'}"></div>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm truncate">{member.name}</p>
            <p class="text-[11px] text-muted-foreground truncate">{member.email || member.role || ''}</p>
          </div>
          {#if member.role}
            <Badge variant="secondary" class="text-[10px] shrink-0">{member.role}</Badge>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
