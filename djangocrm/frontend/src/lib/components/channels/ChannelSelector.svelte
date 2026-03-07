<script>
  import * as Select from '$lib/components/ui/select/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { MessageSquare } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} channels - Available channels
   * @property {string} [value] - Selected channel ID
   * @property {(channelId: string) => void} [onSelect]
   * @property {string} [placeholder]
   */

  /** @type {Props} */
  let { channels = [], value = '', onSelect, placeholder = 'Selecionar canal...' } = $props();

  let selectedLabel = $derived(
    channels.find(c => c.id === value)?.name || placeholder
  );
</script>

<Select.Root type="single" {value} onValueChange={(v) => onSelect?.(v)}>
  <Select.Trigger class="w-full gap-2">
    <MessageSquare class="size-4 text-muted-foreground" />
    {selectedLabel}
  </Select.Trigger>
  <Select.Content>
    {#each channels as channel (channel.id)}
      <Select.Item value={channel.id} disabled={!channel.is_active}>
        <span class="flex items-center gap-2">
          {channel.name}
          {#if !channel.is_active}
            <Badge variant="secondary" class="text-[10px]">Inativo</Badge>
          {/if}
        </span>
      </Select.Item>
    {/each}
    {#if channels.length === 0}
      <div class="px-2 py-4 text-center text-sm text-muted-foreground">
        Nenhum canal disponível
      </div>
    {/if}
  </Select.Content>
</Select.Root>
