<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { QrCode, Copy, Clock, CheckCircle2, XCircle, AlertTriangle, Search, Filter, Plus, ArrowLeft, RefreshCw } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { toast } from 'svelte-sonner';
  import { apiRequest } from '$lib/api-helpers.js';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { orgSettings } from '$lib/stores/org.js';

  const statusOptions = [
    { value: '', label: 'Todos' },
    { value: 'pending', label: 'Pendente' },
    { value: 'confirmed', label: 'Confirmado' },
    { value: 'expired', label: 'Expirado' },
    { value: 'failed', label: 'Falhou' },
    { value: 'refunded', label: 'Estornado' }
  ];

  const typeOptions = [
    { value: '', label: 'Todos' },
    { value: 'pix_qrcode', label: 'PIX QR Code' },
    { value: 'pix_manual', label: 'PIX Manual' },
    { value: 'gateway', label: 'Gateway' }
  ];

  const statusConfig = {
    pending: { label: 'Pendente', icon: Clock, class: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400' },
    confirmed: { label: 'Confirmado', icon: CheckCircle2, class: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400' },
    expired: { label: 'Expirado', icon: XCircle, class: 'bg-gray-50 text-gray-500 dark:bg-gray-500/15 dark:text-gray-400' },
    failed: { label: 'Falhou', icon: AlertTriangle, class: 'bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-400' },
    refunded: { label: 'Estornado', icon: RefreshCw, class: 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400' }
  };

  /** @type {{ data: any }} */
  let { data } = $props();

  const orgCurrency = $derived($orgSettings.default_currency || 'BRL');

  // Filters
  let filterStatus = $state(data.filters?.status || '');
  let filterType = $state(data.filters?.transaction_type || '');
  let filterSearch = $state(data.filters?.search || '');

  // Generate modal
  let showGenerateModal = $state(false);
  let generateAmount = $state('');
  let generateDescription = $state('');
  let generateExpiration = $state('30');
  let generating = $state(false);

  // QR Code result modal
  let showQrModal = $state(false);
  let qrResult = $state(/** @type {any} */ (null));

  // Polling
  let pollingInterval = $state(/** @type {ReturnType<typeof setInterval> | null} */ (null));

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (filterStatus) params.set('status', filterStatus);
    if (filterType) params.set('transaction_type', filterType);
    if (filterSearch) params.set('search', filterSearch);
    const qs = params.toString();
    goto(`/financeiro/pix${qs ? `?${qs}` : ''}`, { invalidateAll: true });
  };

  const handleGenerate = async () => {
    if (!generateAmount || Number(generateAmount) <= 0) {
      toast.error('Informe um valor válido.');
      return;
    }
    generating = true;
    try {
      const result = await apiRequest('/financeiro/pix/generate/', {
        method: 'POST',
        body: {
          amount: generateAmount,
          description: generateDescription,
          expiration_minutes: parseInt(generateExpiration) || 30
        }
      });
      if (result.error) {
        toast.error(result.errors || 'Erro ao gerar PIX.');
      } else {
        showGenerateModal = false;
        qrResult = result;
        showQrModal = true;
        startPolling(result.transaction_id);
        await invalidateAll();
      }
    } catch (err) {
      toast.error('Erro ao gerar PIX.');
    } finally {
      generating = false;
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Código copiado!');
    } catch {
      toast.error('Falha ao copiar.');
    }
  };

  const startPolling = (transactionId) => {
    stopPolling();
    pollingInterval = setInterval(async () => {
      try {
        const tx = await apiRequest(`/financeiro/pix/transactions/${transactionId}/`);
        if (tx.status === 'confirmed') {
          toast.success('Pagamento PIX confirmado!');
          stopPolling();
          qrResult = { ...qrResult, status: 'confirmed' };
          await invalidateAll();
        } else if (tx.status === 'expired' || tx.status === 'failed') {
          stopPolling();
          qrResult = { ...qrResult, status: tx.status };
        }
      } catch {
        // ignore polling errors
      }
    }, 10000);
  };

  const stopPolling = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  };

  const closeQrModal = () => {
    showQrModal = false;
    stopPolling();
    qrResult = null;
  };

  /**
   * @param {string} dateStr
   */
  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  };
</script>

<div class="mx-auto max-w-7xl space-y-6 p-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="icon" onclick={() => goto('/financeiro')}>
        <ArrowLeft class="size-5" />
      </Button>
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Transações PIX</h1>
        <p class="text-muted-foreground text-sm">Gerencie pagamentos PIX e acompanhe confirmações</p>
      </div>
    </div>
    <Button onclick={() => { generateAmount = ''; generateDescription = ''; generateExpiration = '30'; showGenerateModal = true; }}>
      <Plus class="mr-2 size-4" />
      Gerar PIX
    </Button>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-end gap-3">
    <div class="w-48">
      <Select.Root type="single" value={filterStatus} onValueChange={(v) => { filterStatus = v ?? ''; }}>
        <Select.Trigger>{statusOptions.find((o) => o.value === filterStatus)?.label || 'Status'}</Select.Trigger>
        <Select.Content>
          {#each statusOptions as opt (opt.value)}
            <Select.Item value={opt.value}>{opt.label}</Select.Item>
          {/each}
        </Select.Content>
      </Select.Root>
    </div>
    <div class="w-48">
      <Select.Root type="single" value={filterType} onValueChange={(v) => { filterType = v ?? ''; }}>
        <Select.Trigger>{typeOptions.find((o) => o.value === filterType)?.label || 'Tipo'}</Select.Trigger>
        <Select.Content>
          {#each typeOptions as opt (opt.value)}
            <Select.Item value={opt.value}>{opt.label}</Select.Item>
          {/each}
        </Select.Content>
      </Select.Root>
    </div>
    <div class="relative w-56">
      <Search class="text-muted-foreground absolute left-3 top-1/2 size-4 -translate-y-1/2" />
      <Input class="pl-9" placeholder="Buscar txid, pagador..." bind:value={filterSearch} onkeydown={(e) => { if (e.key === 'Enter') applyFilters(); }} />
    </div>
    <Button variant="outline" size="sm" onclick={applyFilters}>
      <Filter class="mr-1 size-3" /> Filtrar
    </Button>
  </div>

  <!-- Transactions Table -->
  {#if data.transactions.length === 0}
    <Card.Root>
      <Card.Content class="flex flex-col items-center justify-center py-12">
        <QrCode class="text-muted-foreground/40 mb-3 size-12" />
        <p class="text-muted-foreground text-sm">Nenhuma transação PIX encontrada.</p>
        <Button variant="outline" size="sm" class="mt-4" onclick={() => { showGenerateModal = true; }}>
          Gerar primeiro PIX
        </Button>
      </Card.Content>
    </Card.Root>
  {:else}
    <Card.Root>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b bg-gray-50/50 dark:bg-gray-900/30">
              <th class="px-4 py-3 text-left font-medium">Status</th>
              <th class="px-4 py-3 text-left font-medium">Tipo</th>
              <th class="px-4 py-3 text-right font-medium">Valor</th>
              <th class="px-4 py-3 text-left font-medium">TXID</th>
              <th class="px-4 py-3 text-left font-medium">Pagador</th>
              <th class="px-4 py-3 text-left font-medium">Criado em</th>
              <th class="px-4 py-3 text-left font-medium">Pago em</th>
            </tr>
          </thead>
          <tbody>
            {#each data.transactions as tx (tx.id)}
              {@const sc = statusConfig[tx.status] || statusConfig.pending}
              <tr class="border-b transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-900/20">
                <td class="px-4 py-3">
                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium {sc.class}">
                    <svelte:component this={sc.icon} class="size-3" />
                    {sc.label}
                  </span>
                </td>
                <td class="px-4 py-3 text-xs">
                  {tx.transaction_type === 'pix_qrcode' ? 'QR Code' : tx.transaction_type === 'pix_manual' ? 'Manual' : 'Gateway'}
                </td>
                <td class="px-4 py-3 text-right font-medium">
                  {formatCurrency(Number(tx.amount), tx.currency || orgCurrency)}
                </td>
                <td class="px-4 py-3">
                  <span class="font-mono text-xs text-gray-500">{tx.pix_txid ? tx.pix_txid.substring(0, 16) + '...' : '—'}</span>
                </td>
                <td class="px-4 py-3 text-xs">{tx.payer_name || tx.contact_name || '—'}</td>
                <td class="px-4 py-3 text-xs text-gray-500">{formatDate(tx.created_at)}</td>
                <td class="px-4 py-3 text-xs text-gray-500">{formatDate(tx.paid_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </Card.Root>
  {/if}
</div>

<!-- Generate PIX Modal -->
<Dialog.Root bind:open={showGenerateModal}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Gerar PIX QR Code</Dialog.Title>
      <Dialog.Description>Preencha os dados para gerar um código PIX.</Dialog.Description>
    </Dialog.Header>
    <div class="space-y-4 py-4">
      <div class="space-y-2">
        <Label for="pix-amount">Valor (R$)</Label>
        <Input id="pix-amount" type="number" step="0.01" min="0.01" placeholder="0,00" bind:value={generateAmount} />
      </div>
      <div class="space-y-2">
        <Label for="pix-desc">Descrição</Label>
        <Input id="pix-desc" placeholder="Descrição do pagamento" bind:value={generateDescription} />
      </div>
      <div class="space-y-2">
        <Label for="pix-exp">Expiração (minutos)</Label>
        <Input id="pix-exp" type="number" min="1" max="1440" bind:value={generateExpiration} />
      </div>
    </div>
    <Dialog.Footer>
      <Button variant="outline" onclick={() => { showGenerateModal = false; }}>Cancelar</Button>
      <Button onclick={handleGenerate} disabled={generating}>
        {generating ? 'Gerando...' : 'Gerar PIX'}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- QR Code Result Modal -->
<Dialog.Root open={showQrModal} onOpenChange={(v) => { if (!v) closeQrModal(); }}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>PIX QR Code</Dialog.Title>
      <Dialog.Description>
        {#if qrResult?.status === 'confirmed'}
          Pagamento confirmado!
        {:else}
          Escaneie o QR Code ou copie o código para pagar.
        {/if}
      </Dialog.Description>
    </Dialog.Header>
    {#if qrResult}
      <div class="flex flex-col items-center gap-4 py-4">
        {#if qrResult.status === 'confirmed'}
          <div class="flex size-32 items-center justify-center rounded-full bg-emerald-50 dark:bg-emerald-500/15">
            <CheckCircle2 class="size-16 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p class="text-lg font-semibold text-emerald-600">Pagamento Confirmado</p>
        {:else if qrResult.qr_code_base64}
          <img
            src="data:image/png;base64,{qrResult.qr_code_base64}"
            alt="PIX QR Code"
            class="size-48 rounded-lg border"
          />
        {:else}
          <div class="flex size-48 items-center justify-center rounded-lg border bg-gray-50">
            <QrCode class="text-muted-foreground size-16" />
          </div>
        {/if}

        {#if qrResult.pix_copy_paste && qrResult.status !== 'confirmed'}
          <div class="w-full space-y-2">
            <Label>Copia e Cola</Label>
            <div class="flex gap-2">
              <Input value={qrResult.pix_copy_paste} readonly class="font-mono text-xs" />
              <Button variant="outline" size="icon" onclick={() => copyToClipboard(qrResult.pix_copy_paste)}>
                <Copy class="size-4" />
              </Button>
            </div>
          </div>
        {/if}

        {#if qrResult.expires_at && qrResult.status !== 'confirmed'}
          <p class="text-muted-foreground text-xs">
            Expira em: {formatDate(qrResult.expires_at)}
          </p>
        {/if}
      </div>
    {/if}
    <Dialog.Footer>
      <Button onclick={closeQrModal}>Fechar</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
