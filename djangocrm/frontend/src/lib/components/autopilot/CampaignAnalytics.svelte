<script>
  import { apiRequest } from '$lib/api.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import {
    Send, Eye, MousePointer, AlertTriangle,
    UserMinus, Mail, CheckCircle, RefreshCw
  } from '@lucide/svelte';

  let { campaignId } = $props();

  let analytics = $state(null);
  let recipients = $state([]);
  let recipientTotal = $state(0);
  let recipientFilter = $state('');
  let loading = $state(true);
  let error = $state('');

  const statusLabels = {
    pending: 'Pendente', sent: 'Enviado', delivered: 'Entregue',
    opened: 'Aberto', clicked: 'Clicado', bounced: 'Bounce',
    failed: 'Falhou', unsubscribed: 'Descadastrado'
  };
  const statusVariants = {
    pending: 'secondary', sent: 'outline', delivered: 'default',
    opened: 'default', clicked: 'default', bounced: 'destructive',
    failed: 'destructive', unsubscribed: 'outline'
  };

  async function loadData() {
    loading = true;
    error = '';
    try {
      const params = { limit: '50', offset: '0' };
      if (recipientFilter) params.status = recipientFilter;
      const [analyticsData, recipientsData] = await Promise.all([
        apiRequest(`/campaigns/${campaignId}/analytics/`),
        apiRequest(`/campaigns/${campaignId}/recipients/?${new URLSearchParams(params).toString()}`)
      ]);
      analytics = analyticsData || {};
      recipients = recipientsData?.results || [];
      recipientTotal = recipientsData?.total || recipientsData?.count || 0;
    } catch (err) {
      error = err?.message || 'Erro ao carregar analytics.';
    } finally {
      loading = false;
    }
  }

  function filterRecipients(status) {
    recipientFilter = status;
    loadData();
  }

  // Load data on mount
  $effect(() => {
    if (campaignId) loadData();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-8">
    <RefreshCw class="size-5 animate-spin text-muted-foreground" />
    <span class="ml-2 text-sm text-muted-foreground">Carregando analytics...</span>
  </div>
{:else if error}
  <div class="text-sm text-destructive py-4 text-center">{error}</div>
{:else if analytics}
  <div class="space-y-5">
    <!-- Metric Cards -->
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-lg border p-3">
        <div class="flex items-center gap-2">
          <Send class="text-muted-foreground size-4" />
          <span class="text-muted-foreground text-sm">Enviados</span>
        </div>
        <p class="mt-1 text-xl font-bold">{analytics.sent_count || 0}</p>
        <p class="text-muted-foreground text-xs">de {analytics.total_recipients || 0}</p>
      </div>

      <div class="rounded-lg border p-3">
        <div class="flex items-center gap-2">
          <CheckCircle class="text-muted-foreground size-4" />
          <span class="text-muted-foreground text-sm">Taxa de Entrega</span>
        </div>
        <p class="mt-1 text-xl font-bold">{analytics.delivery_rate || 0}%</p>
        <p class="text-muted-foreground text-xs">{analytics.delivered_count || 0} entregues</p>
      </div>

      <div class="rounded-lg border p-3">
        <div class="flex items-center gap-2">
          <Eye class="text-muted-foreground size-4" />
          <span class="text-muted-foreground text-sm">Taxa de Abertura</span>
        </div>
        <p class="mt-1 text-xl font-bold">{analytics.open_rate || 0}%</p>
        <p class="text-muted-foreground text-xs">{analytics.opened_count || 0} abertos</p>
      </div>

      <div class="rounded-lg border p-3">
        <div class="flex items-center gap-2">
          <MousePointer class="text-muted-foreground size-4" />
          <span class="text-muted-foreground text-sm">Taxa de Clique</span>
        </div>
        <p class="mt-1 text-xl font-bold">{analytics.click_rate || 0}%</p>
        <p class="text-muted-foreground text-xs">{analytics.clicked_count || 0} cliques</p>
      </div>
    </div>

    <!-- Secondary metrics -->
    <div class="grid gap-3 sm:grid-cols-3">
      <div class="flex items-center gap-3 rounded-lg border p-3">
        <AlertTriangle class="text-destructive size-4" />
        <div>
          <p class="text-sm font-medium">{analytics.failed_count || 0} falhas</p>
          <p class="text-muted-foreground text-xs">{analytics.bounce_count || 0} bounces</p>
        </div>
      </div>
      <div class="flex items-center gap-3 rounded-lg border p-3">
        <UserMinus class="text-muted-foreground size-4" />
        <p class="text-sm font-medium">{analytics.unsubscribed_count || 0} descadastrados</p>
      </div>
      <div class="flex items-center gap-3 rounded-lg border p-3">
        <Mail class="text-muted-foreground size-4" />
        <div>
          <p class="text-sm font-medium">{analytics.total_recipients || 0} total</p>
          <p class="text-muted-foreground text-xs">destinatários</p>
        </div>
      </div>
    </div>

    <!-- Recipients Table -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold">Destinatários</h3>
        <div class="flex gap-1.5">
          <Button variant={!recipientFilter ? 'default' : 'outline'} size="sm" class="h-7 text-xs" onclick={() => filterRecipients('')}>Todos</Button>
          <Button variant={recipientFilter === 'sent' ? 'default' : 'outline'} size="sm" class="h-7 text-xs" onclick={() => filterRecipients('sent')}>Enviados</Button>
          <Button variant={recipientFilter === 'opened' ? 'default' : 'outline'} size="sm" class="h-7 text-xs" onclick={() => filterRecipients('opened')}>Abertos</Button>
          <Button variant={recipientFilter === 'failed' ? 'default' : 'outline'} size="sm" class="h-7 text-xs" onclick={() => filterRecipients('failed')}>Falhas</Button>
        </div>
      </div>

      {#if recipients.length === 0}
        <div class="text-muted-foreground rounded-lg border border-dashed py-6 text-center text-sm">
          Nenhum destinatário encontrado.
        </div>
      {:else}
        <div class="overflow-x-auto rounded-lg border">
          <table class="w-full text-sm">
            <thead class="bg-muted/50 border-b">
              <tr>
                <th class="px-3 py-2 text-left font-medium">Contato</th>
                <th class="px-3 py-2 text-left font-medium">Email</th>
                <th class="px-3 py-2 text-left font-medium">Status</th>
                <th class="px-3 py-2 text-left font-medium">Enviado em</th>
                <th class="px-3 py-2 text-left font-medium">Aberto em</th>
              </tr>
            </thead>
            <tbody>
              {#each recipients as recipient (recipient.id)}
                <tr class="border-b last:border-0">
                  <td class="px-3 py-2">{recipient.contact_name || '—'}</td>
                  <td class="text-muted-foreground px-3 py-2 text-xs">{recipient.contact_email || '—'}</td>
                  <td class="px-3 py-2">
                    <Badge variant={statusVariants[recipient.status] || 'secondary'} class="text-[10px]">
                      {statusLabels[recipient.status] || recipient.status}
                    </Badge>
                  </td>
                  <td class="text-muted-foreground px-3 py-2 text-xs">
                    {recipient.sent_at ? new Date(recipient.sent_at).toLocaleString('pt-BR') : '—'}
                  </td>
                  <td class="text-muted-foreground px-3 py-2 text-xs">
                    {recipient.opened_at ? new Date(recipient.opened_at).toLocaleString('pt-BR') : '—'}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="text-muted-foreground text-xs">{recipientTotal} destinatários no total</p>
      {/if}
    </div>
  </div>
{/if}
