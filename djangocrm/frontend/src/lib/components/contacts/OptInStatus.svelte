<script>
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Mail, MessageSquare, CheckCircle, XCircle, AlertTriangle } from '@lucide/svelte';

  /**
   * Exibe status de opt-in/opt-out para SMS e email de um contato.
   *
   * @typedef {Object} Props
   * @property {boolean} [smsOptIn]
   * @property {boolean} [emailOptIn]
   * @property {(channel: string, optIn: boolean) => void} [onToggle]
   */

  /** @type {Props} */
  let { smsOptIn = true, emailOptIn = true, onToggle } = $props();
</script>

<div class="space-y-2">
  <h4 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Consentimento</h4>

  <div class="flex flex-wrap gap-2">
    <!-- SMS -->
    <div class="flex items-center gap-1.5">
      <MessageSquare class="size-3.5 text-muted-foreground" />
      {#if smsOptIn}
        <Badge variant="outline" class="gap-1 text-[10px] border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-400">
          <CheckCircle class="size-2.5" />
          SMS ativo
        </Badge>
      {:else}
        <Badge variant="outline" class="gap-1 text-[10px] border-red-200 text-red-700 dark:border-red-800 dark:text-red-400">
          <XCircle class="size-2.5" />
          SMS opt-out
        </Badge>
      {/if}
      <Button variant="ghost" size="sm" class="h-5 px-1.5 text-[10px]" onclick={() => onToggle?.('sms', !smsOptIn)}>
        {smsOptIn ? 'Desativar' : 'Ativar'}
      </Button>
    </div>

    <!-- Email -->
    <div class="flex items-center gap-1.5">
      <Mail class="size-3.5 text-muted-foreground" />
      {#if emailOptIn}
        <Badge variant="outline" class="gap-1 text-[10px] border-emerald-200 text-emerald-700 dark:border-emerald-800 dark:text-emerald-400">
          <CheckCircle class="size-2.5" />
          Email ativo
        </Badge>
      {:else}
        <Badge variant="outline" class="gap-1 text-[10px] border-red-200 text-red-700 dark:border-red-800 dark:text-red-400">
          <XCircle class="size-2.5" />
          Email opt-out
        </Badge>
      {/if}
      <Button variant="ghost" size="sm" class="h-5 px-1.5 text-[10px]" onclick={() => onToggle?.('email', !emailOptIn)}>
        {emailOptIn ? 'Desativar' : 'Ativar'}
      </Button>
    </div>
  </div>

  {#if !smsOptIn || !emailOptIn}
    <div class="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
      <AlertTriangle class="size-3.5" />
      Contato em opt-out para {!smsOptIn && !emailOptIn ? 'SMS e Email' : !smsOptIn ? 'SMS' : 'Email'}
    </div>
  {/if}
</div>
