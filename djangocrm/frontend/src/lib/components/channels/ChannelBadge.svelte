<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Phone, Instagram, Send, Mail, Globe, MessageSquare } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} channelType
   * @property {string} [name]
   */

  /** @type {Props} */
  let { channelType = '', name = '' } = $props();

  /** @type {Record<string, {icon: any, label: string}>} */
  const channelMap = {
    whatsapp: { icon: Phone, label: 'WhatsApp' },
    whatsapp_cloud: { icon: Phone, label: 'WhatsApp Cloud' },
    instagram: { icon: Instagram, label: 'Instagram' },
    facebook: { icon: MessageSquare, label: 'Facebook' },
    telegram: { icon: Send, label: 'Telegram' },
    sms: { icon: MessageSquare, label: 'SMS' },
    email: { icon: Mail, label: 'Email' },
    smtp_native: { icon: Mail, label: 'Email' },
    web_chat: { icon: Globe, label: 'Web Chat' },
  };

  let config = $derived(channelMap[channelType] || { icon: MessageSquare, label: name || channelType });
</script>

<Badge variant="outline" class="gap-1 text-xs">
  {#if channelType === 'whatsapp' || channelType === 'whatsapp_cloud'}
    <Phone class="size-3" />
  {:else if channelType === 'instagram'}
    <Instagram class="size-3" />
  {:else if channelType === 'telegram'}
    <Send class="size-3" />
  {:else if channelType === 'email' || channelType === 'smtp_native'}
    <Mail class="size-3" />
  {:else if channelType === 'web_chat'}
    <Globe class="size-3" />
  {:else}
    <MessageSquare class="size-3" />
  {/if}
  {name || config.label}
</Badge>
