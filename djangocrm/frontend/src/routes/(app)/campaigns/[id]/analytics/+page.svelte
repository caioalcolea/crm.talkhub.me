<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import {
    ArrowLeft, Send, Eye, MousePointer, AlertTriangle,
    UserMinus, Mail, CheckCircle
  } from '@lucide/svelte';

  let { data } = $props();

  let analytics = $derived(data.analytics || {});
  let recipients = $derived(data.recipients || []);
  let filters = $derived(data.filters || {});

  const statusLabels = {
    pending: 'Pendente',
    sent: 'Enviado',
    delivered: 'Entregue',
    opened: 'Aberto',
    clicked: 'Clicado',
    bounced: 'Bounce',
    failed: 'Falhou',
    unsubscribed: 'Descadastrado'
  };

  const statusVariants = {
    pending: 'secondary',
    sent: 'outline',
    delivered: 'default',
    opened: 'default',
    clicked: 'default',
    bounced: 'destructive',
    failed: 'destructive',
    unsubscribed: 'outline'
  };

  /**
   * @param {string} recipientStatus
   */
  function filterRecipients(recipientStatus) {
    const url = new URL($page.url);
    if (recipientStatus) {
      url.searchParams.set('recipient_status', recipientStatus);
    } else {
      url.searchParams.delete('recipient_status');
    }
    goto(url.toString());
  }
</script>

<svelte:head>
  <title>{analytics.name || 'Analytics'} — Campanhas — TalkHub CRM</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-6 p-6">
  <!-- Header -->
  <div class="flex items-center gap-3">
    <Button href="/campaigns" variant="ghost" size="icon" class="size-8">
      <ArrowLeft class="size-4" />
    </Button>
    <div>
      <h1 class="text-2xl font-bold tracking-tight">{analytics.name || 'Campanha'}</h1>
      <div class="flex items-center gap-2">
        <Badge variant="secondary" class="text-xs">{analytics.campaign_type || ''}</Badge>
        <Badge variant="outline" class="text-xs">{analytics.status || ''}</Badge>
      </div>
    </div>
  </div>

  <!-- Metric Cards -->
  <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <div class="rounded-lg border p-4">
      <div class="flex items-center gap-2">
        <Send class="text-muted-foreground size-4" />
        <span class="text-muted-foreground text-sm">Enviados</span>
      </div>
      <p class="mt-1 text-2xl font-bold">{analytics.sent_count || 0}</p>
      <p class="text-muted-foreground text-xs">de {analytics.total_recipients || 0} destinatários</p>
    </div>

    <div class="rounded-lg border p-4">
      <div class="flex items-center gap-2">
        <CheckCircle class="text-muted-foreground size-4" />
        <span class="text-muted-foreground text-sm">Taxa de Entrega</span>
      </div>
      <p class="mt-1 text-2xl font-bold">{analytics.delivery_rate || 0}%</p>
      <p class="text-muted-foreground text-xs">{analytics.delivered_count || 0} entregues</p>
    </div>

    <div class="rounded-lg border p-4">
      <div class="flex items-center gap-2">
        <Eye class="text-muted-foreground size-4" />
        <span class="text-muted-foreground text-sm">Taxa de Abertura</span>
      </div>
      <p class="mt-1 text-2xl font-bold">{analytics.open_rate || 0}%</p>
      <p class="text-muted-foreground text-xs">{analytics.opened_count || 0} abertos</p>
    </div>

    <div class="rounded-lg border p-4">
      <div class="flex items-center gap-2">
        <MousePointer class="text-muted-foreground size-4" />
        <span class="text-muted-foreground text-sm">Taxa de Clique</span>
      </div>
      <p class="mt-1 text-2xl font-bold">{analytics.click_rate || 0}%</p>
      <p class="text-muted-foreground text-xs">{analytics.clicked_count || 0} cliques</p>
    </div>
  </div>

  <!-- Secondary metrics -->
  <div class="grid gap-4 sm:grid-cols-3">
    <div class="flex items-center gap-3 rounded-lg border p-3">
      <AlertTriangle class="text-destructive size-5" />
      <div>
        <p class="text-sm font-medium">{analytics.failed_count || 0} falhas</p>
        <p class="text-muted-foreground text-xs">{analytics.bounce_count || 0} bounces</p>
      </div>
    </div>
    <div class="flex items-center gap-3 rounded-lg border p-3">
      <UserMinus class="text-muted-foreground size-5" />
      <div>
        <p class="text-sm font-medium">{analytics.unsubscribed_count || 0} descadastrados</p>
      </div>
    </div>
    <div class="flex items-center gap-3 rounded-lg border p-3">
      <Mail class="text-muted-foreground size-5" />
      <div>
        <p class="text-sm font-medium">{analytics.total_recipients || 0} total</p>
        <p class="text-muted-foreground text-xs">destinatários na campanha</p>
      </div>
    </div>
  </div>

  <!-- Recipients Table -->
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold">Destinatários</h2>
      <div class="flex gap-2">
        <Button
          variant={!filters.recipient_status ? 'default' : 'outline'}
          size="sm"
          onclick={() => filterRecipients('')}
        >
          Todos
        </Button>
        <Button
          variant={filters.recipient_status === 'sent' ? 'default' : 'outline'}
          size="sm"
          onclick={() => filterRecipients('sent')}
        >
          Enviados
        </Button>
        <Button
          variant={filters.recipient_status === 'opened' ? 'default' : 'outline'}
          size="sm"
          onclick={() => filterRecipients('opened')}
        >
          Abertos
        </Button>
        <Button
          variant={filters.recipient_status === 'failed' ? 'default' : 'outline'}
          size="sm"
          onclick={() => filterRecipients('failed')}
        >
          Falhas
        </Button>
      </div>
    </div>

    {#if recipients.length === 0}
      <div class="text-muted-foreground rounded-lg border border-dashed py-8 text-center text-sm">
        Nenhum destinatário encontrado.
      </div>
    {:else}
      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full text-sm">
          <thead class="bg-muted/50 border-b">
            <tr>
              <th class="px-4 py-2 text-left font-medium">Contato</th>
              <th class="px-4 py-2 text-left font-medium">Email</th>
              <th class="px-4 py-2 text-left font-medium">Status</th>
              <th class="px-4 py-2 text-left font-medium">Enviado em</th>
              <th class="px-4 py-2 text-left font-medium">Aberto em</th>
            </tr>
          </thead>
          <tbody>
            {#each recipients as recipient (recipient.id)}
              <tr class="border-b last:border-0">
                <td class="px-4 py-2">{recipient.contact_name || '—'}</td>
                <td class="text-muted-foreground px-4 py-2 text-xs">{recipient.contact_email || '—'}</td>
                <td class="px-4 py-2">
                  <Badge variant={statusVariants[recipient.status] || 'secondary'} class="text-[10px]">
                    {statusLabels[recipient.status] || recipient.status}
                  </Badge>
                </td>
                <td class="text-muted-foreground px-4 py-2 text-xs">
                  {recipient.sent_at ? new Date(recipient.sent_at).toLocaleString('pt-BR') : '—'}
                </td>
                <td class="text-muted-foreground px-4 py-2 text-xs">
                  {recipient.opened_at ? new Date(recipient.opened_at).toLocaleString('pt-BR') : '—'}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="text-muted-foreground text-xs">{data.recipientTotal} destinatários no total</p>
    {/if}
  </div>
</div>
