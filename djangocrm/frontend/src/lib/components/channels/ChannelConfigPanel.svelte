<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Switch } from '$lib/components/ui/switch/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import { Wifi, Save } from '@lucide/svelte';
  import ChannelBadge from './ChannelBadge.svelte';

  /**
   * @typedef {Object} Props
   * @property {any} channel
   * @property {(data: any) => void} [onSave]
   * @property {() => void} [onTest]
   * @property {boolean} [testing]
   * @property {boolean} [saving]
   */

  /** @type {Props} */
  let { channel = {}, onSave, onTest, testing = false, saving = false } = $props();
</script>

<div class="space-y-4">
  <div class="flex items-center justify-between">
    <ChannelBadge channelType={channel.channel_type} name={channel.name} />
    <div class="flex items-center gap-2">
      <span class="text-xs text-muted-foreground">Ativo</span>
      <Switch checked={channel.is_active} />
    </div>
  </div>

  <Separator />

  {#if channel.config_fields}
    <div class="space-y-3">
      {#each Object.entries(channel.config_fields) as [key, field]}
        <div class="space-y-1">
          <Label for={key}>{field.label || key}</Label>
          <Input id={key} value={channel.config?.[key] || ''} placeholder={field.placeholder || ''} />
        </div>
      {/each}
    </div>
  {/if}

  <div class="flex gap-2 pt-2">
    {#if onTest}
      <Button variant="outline" size="sm" onclick={onTest} disabled={testing} class="gap-2">
        <Wifi class="size-4" />
        {testing ? 'Testando...' : 'Testar'}
      </Button>
    {/if}
    {#if onSave}
      <Button size="sm" onclick={() => onSave(channel)} disabled={saving} class="gap-2">
        <Save class="size-4" />
        {saving ? 'Salvando...' : 'Salvar'}
      </Button>
    {/if}
  </div>
</div>
