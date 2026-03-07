<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Switch } from '$lib/components/ui/switch/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Wifi, MessageSquare, Instagram, Send, Mail, Globe, Phone } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} channels
   * @property {(channel: any, enabled: boolean) => void} [onToggle]
   * @property {(channel: any) => void} [onTest]
   */

  /** @type {Props} */
  let { channels = [], onToggle, onTest } = $props();

  /** @type {Record<string, any>} */
  const channelIcons = {
    whatsapp: Phone,
    whatsapp_cloud: Phone,
    whatsapp_groups: MessageSquare,
    instagram: Instagram,
    facebook: MessageSquare,
    telegram: Send,
    sms: MessageSquare,
    web_chat: Globe,
    email: Mail,
  };

  /** @param {string} type */
  function getIcon(type) {
    return channelIcons[type] || MessageSquare;
  }
</script>

<div class="space-y-3">
  {#each channels as channel (channel.id)}
    {@const Icon = getIcon(channel.channel_type)}
    <div class="bg-muted/50 flex items-center gap-3 rounded-lg p-3">
      <Icon class="size-5 text-muted-foreground shrink-0" />
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium truncate">{channel.name || channel.channel_type}</p>
        {#if channel.identifier}
          <p class="text-muted-foreground text-xs truncate">{channel.identifier}</p>
        {/if}
      </div>
      <Badge variant={channel.is_active ? 'default' : 'secondary'} class="text-xs shrink-0">
        {channel.is_active ? 'Ativo' : 'Inativo'}
      </Badge>
      {#if onTest}
        <Button variant="ghost" size="sm" onclick={() => onTest(channel)} class="gap-1 shrink-0">
          <Wifi class="size-3.5" />
          Testar
        </Button>
      {/if}
      {#if onToggle}
        <Switch checked={channel.is_active} onCheckedChange={(v) => onToggle(channel, v)} />
      {/if}
    </div>
  {/each}
  {#if channels.length === 0}
    <p class="text-muted-foreground text-sm text-center py-4">Nenhum canal configurado.</p>
  {/if}
</div>
