<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import ChatDrawer from './ChatDrawer.svelte';
  import { MessageCircle } from '@lucide/svelte';

  /**
   * Botão "Ver Conversa" — exibe somente quando contato tem omni_user_ns ou talkhub_subscriber_id.
   * Ao clicar, abre o ChatDrawer com a timeline do contato.
   *
   * @typedef {Object} Props
   * @property {string} contactId - UUID do contato
   * @property {string} [omniUserNs] - omni_user_ns do contato
   * @property {string} [subscriberId] - talkhub_subscriber_id do contato
   * @property {string} [variant] - Button variant
   * @property {string} [size] - Button size
   */

  /** @type {Props} */
  let { contactId, omniUserNs = '', subscriberId = '', variant = 'outline', size = 'sm' } = $props();

  let drawerOpen = $state(false);
  let hasConversation = $derived(!!omniUserNs || !!subscriberId);
</script>

{#if hasConversation}
  <Button {variant} {size} class="gap-1.5" onclick={() => drawerOpen = true}>
    <MessageCircle class="size-4" />
    Ver Conversa
  </Button>

  <ChatDrawer {contactId} open={drawerOpen} onOpenChange={(v) => drawerOpen = v} />
{/if}
