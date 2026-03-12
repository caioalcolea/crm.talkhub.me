<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import * as Tooltip from '$lib/components/ui/tooltip/index.js';
  import IntegrationHealth from './IntegrationHealth.svelte';
  import { apiRequest } from '$lib/api.js';
  import {
    Wifi, WifiOff, RefreshCw, Copy, Check, Eye, EyeOff,
    CircleHelp, Zap, Webhook, Save, AlertTriangle, Clock,
    ChevronDown, ChevronUp, RotateCcw, Radio, MessageCircle,
    Loader2, Shield
  } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any} integration
   * @property {any} health
   * @property {any[]} [fieldMappings]
   * @property {any[]} [dlqItems]
   * @property {string} webhookUrl
   * @property {any} [form]
   */

  /** @type {Props} */
  let { integration, health, fieldMappings = [], dlqItems = [], webhookUrl, form } = $props();

  let isConnected = $derived(integration?.is_connected && integration?.is_active);
  let isTesting = $state(false);
  let isSyncing = $state(false);
  let showPassword = $state(false);
  let showWebhookSecret = $state(false);
  let webhookCopied = $state(false);
  let fetchingPubsub = $state(false);
  let showTroubleshooting = $state(false);

  // Sync interval friendly options
  const syncIntervalOptions = [
    { value: '5', label: 'A cada 5 minutos' },
    { value: '15', label: 'A cada 15 minutos' },
    { value: '30', label: 'A cada 30 minutos' },
    { value: '60', label: 'A cada 1 hora' },
  ];

  const conflictOptions = [
    { value: 'last_write_wins', label: 'Manter o último atualizado' },
    { value: 'crm_wins', label: 'O CRM tem prioridade' },
    { value: 'external_wins', label: 'O Chatwoot tem prioridade' },
  ];

  function copyWebhookUrl() {
    if (typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(webhookUrl);
      webhookCopied = true;
      setTimeout(() => { webhookCopied = false; }, 2000);
    }
  }

  async function fetchPubsubToken() {
    fetchingPubsub = true;
    try {
      const result = await apiRequest('/integrations/chatwoot/fetch-pubsub-token/', { method: 'POST' });
      if (result?.pubsub_token) {
        toast.success('PubSub Token extraído com sucesso!');
        // Force page reload to get updated config
        window.location.reload();
      } else {
        toast.error(result?.error || 'PubSub token não encontrado');
      }
    } catch (e) {
      toast.error(e?.message || 'Falha ao buscar PubSub Token');
    } finally {
      fetchingPubsub = false;
    }
  }

  $effect(() => {
    if (form?.saved) toast.success('Configuracao salva');
    if (form?.connected) toast.success('Integracao conectada com sucesso!');
    if (form?.disconnected) toast.success('Integracao desconectada');
    if (form?.syncStarted) toast.success('Sincronizacao iniciada');
    if (form?.syncIntervalSaved) toast.success('Intervalo de sincronizacao salvo');
    if (form?.dlqReprocessed) toast.success('Webhook reenfileirado para reprocessamento');
    if (form?.error) toast.error(form.error);
    if (form?.testResult) toast.success('Conexao testada: ' + (form.testResult.status || 'OK'));
    if (form?.testError) toast.error(form.testError);
    if (form?.syncError) toast.error(form.syncError);
  });

  let configValues = $derived(integration?.config || {});
  let hasPubsub = $derived(!!configValues.pubsub_token);
</script>

<div class="space-y-6">
  <!-- ====== Section 1: Status Header ====== -->
  <Card.Root>
    <Card.Header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="flex size-10 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-950">
            <MessageCircle class="size-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <Card.Title>{integration.name || 'Chatwoot'}</Card.Title>
            <Card.Description>Integração de chat em tempo real</Card.Description>
          </div>
        </div>
        <IntegrationHealth status={health?.status || integration.health_status || 'unknown'} />
      </div>
    </Card.Header>
    <Card.Content class="space-y-4">
      <!-- Status Badges -->
      <div class="flex flex-wrap items-center gap-2">
        <Badge variant={isConnected ? 'default' : 'destructive'} class="gap-1.5">
          {#if isConnected}
            <Wifi class="size-3" /> Conectado
          {:else}
            <WifiOff class="size-3" /> Desconectado
          {/if}
        </Badge>
        <Badge variant={integration?.webhook_token ? 'default' : 'secondary'} class="gap-1.5">
          <Webhook class="size-3" />
          {integration?.webhook_token ? 'Webhook Ativo' : 'Webhook Pendente'}
        </Badge>
        <Badge variant={hasPubsub ? 'default' : 'outline'} class="gap-1.5">
          <Radio class="size-3" />
          {hasPubsub ? 'Tempo Real Ativo' : 'Tempo Real Inativo'}
        </Badge>
        {#if integration.last_sync_at}
          <span class="text-muted-foreground text-xs ml-auto">
            <Clock class="inline size-3 mr-0.5" />
            Ultimo sync: {new Date(integration.last_sync_at).toLocaleString('pt-BR')}
          </span>
        {/if}
      </div>

      <Separator />

      <!-- Quick Actions -->
      <div class="flex flex-wrap gap-2">
        <form method="POST" action="?/testConnection" use:enhance={() => {
          isTesting = true;
          return async ({ update }) => { isTesting = false; await update(); };
        }}>
          <Button variant="outline" type="submit" disabled={isTesting || !isConnected} class="gap-2" size="sm">
            <Wifi class="size-4" />
            {isTesting ? 'Testando...' : 'Testar Conexao'}
          </Button>
        </form>

        <form method="POST" action="?/syncNow" use:enhance={() => {
          isSyncing = true;
          return async ({ update }) => { isSyncing = false; await update(); };
        }}>
          <Button variant="outline" type="submit" disabled={isSyncing || !isConnected} class="gap-2" size="sm">
            <RefreshCw class="size-4 {isSyncing ? 'animate-spin' : ''}" />
            {isSyncing ? 'Sincronizando...' : 'Sincronizar Agora'}
          </Button>
        </form>

        {#if integration.is_active}
          <form method="POST" action="?/disconnect" use:enhance>
            <Button variant="outline" type="submit" class="gap-2 text-destructive hover:bg-destructive/10" size="sm">
              <WifiOff class="size-4" />
              Desconectar
            </Button>
          </form>
        {/if}

        <!-- Help Dialog -->
        <Dialog.Root>
          <Dialog.Trigger>
            <button type="button" class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
              <CircleHelp class="size-4" />
              Como conectar?
            </button>
          </Dialog.Trigger>
          <Dialog.Content class="max-w-xl max-h-[85vh] overflow-y-auto">
            <Dialog.Header>
              <Dialog.Title>Como conectar o Chatwoot</Dialog.Title>
              <Dialog.Description>Siga os 3 passos para configurar a integracao.</Dialog.Description>
            </Dialog.Header>
            <div class="space-y-4 text-sm">
              <!-- Step 1 -->
              <div class="rounded-lg border p-4 space-y-2">
                <div class="flex items-center gap-2">
                  <span class="flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">1</span>
                  <p class="font-semibold">Encontre suas credenciais</p>
                </div>
                <p class="text-muted-foreground">
                  <strong>Account ID:</strong> Va em <code>Settings &rarr; Account Settings</code>. O ID esta na URL:
                </p>
                <div class="bg-muted rounded-md px-3 py-2 font-mono text-xs">
                  .../accounts/<strong class="text-foreground">1</strong>/settings/general
                </div>
                <p class="text-muted-foreground">
                  <strong>Access Token:</strong> Clique no seu avatar &rarr; <code>Profile Settings</code> &rarr; <code>Access Token</code>
                </p>
              </div>

              <!-- Step 2 -->
              <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-2 dark:border-blue-800 dark:bg-blue-950">
                <div class="flex items-center gap-2">
                  <span class="flex size-6 items-center justify-center rounded-full bg-blue-600 text-white text-xs font-bold">2</span>
                  <p class="font-semibold text-blue-800 dark:text-blue-200">Habilite o Tempo Real (WebSocket)</p>
                </div>
                <p class="text-blue-700 dark:text-blue-300">
                  Apos inserir o URL e Token de Acesso, clique no botao <strong>"Buscar Automaticamente"</strong> na secao de credenciais.
                  O TalkHub extrai o PubSub Token diretamente do Chatwoot.
                </p>
              </div>

              <!-- Step 3 -->
              <div class="rounded-lg border border-green-200 bg-green-50 p-4 space-y-2 dark:border-green-800 dark:bg-green-950">
                <div class="flex items-center gap-2">
                  <span class="flex size-6 items-center justify-center rounded-full bg-green-600 text-white text-xs font-bold">3</span>
                  <p class="font-semibold text-green-800 dark:text-green-200">Salvar e Conectar</p>
                </div>
                <p class="text-green-700 dark:text-green-300">
                  Preencha os campos e clique em <strong>"Salvar e Conectar"</strong>.
                  O webhook sera registrado automaticamente no Chatwoot.
                </p>
              </div>
            </div>
            <Dialog.Footer>
              <Dialog.Close>
                <Button variant="outline">Entendi</Button>
              </Dialog.Close>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Root>
      </div>
    </Card.Content>
  </Card.Root>

  <!-- ====== Section 2: Credentials ====== -->
  <Card.Root>
    <Card.Header>
      <Card.Title class="text-base flex items-center gap-2">
        <Shield class="size-4" />
        Credenciais da Conta
      </Card.Title>
      <Card.Description>Configure as credenciais de acesso ao Chatwoot</Card.Description>
    </Card.Header>
    <Card.Content>
      <form method="POST" action="?/saveConfig" use:enhance>
        <div class="space-y-4">
          <!-- Chatwoot URL -->
          <div class="space-y-2">
            <Label for="chatwoot_url">URL da Instancia Chatwoot</Label>
            <Input
              id="chatwoot_url"
              name="chatwoot_url"
              type="url"
              placeholder="https://chat.suaempresa.com.br"
              value={configValues.chatwoot_url || ''}
              required
            />
          </div>

          <!-- API Access Token -->
          <div class="space-y-2">
            <Label for="api_access_token">Token de Acesso (API)</Label>
            <div class="relative">
              <Input
                id="api_access_token"
                name="api_access_token"
                type={showPassword ? 'text' : 'password'}
                placeholder="Cole o Access Token do Chatwoot"
                value={configValues.api_access_token || ''}
                required
                class="pr-10"
              />
              <button
                type="button"
                onclick={() => showPassword = !showPassword}
                class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {#if showPassword}
                  <EyeOff class="size-4" />
                {:else}
                  <Eye class="size-4" />
                {/if}
              </button>
            </div>
            <p class="text-muted-foreground text-xs">Perfil &rarr; Access Token no Chatwoot</p>
          </div>

          <!-- Account ID -->
          <div class="space-y-2">
            <Label for="account_id">ID da Conta</Label>
            <Input
              id="account_id"
              name="account_id"
              type="number"
              placeholder="1"
              value={configValues.account_id || ''}
              required
              class="w-32"
            />
          </div>

          <!-- PubSub Token -->
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <Label for="pubsub_token">Token de Tempo Real (PubSub)</Label>
              <Tooltip.Root>
                <Tooltip.Trigger>
                  <CircleHelp class="size-3.5 text-muted-foreground" />
                </Tooltip.Trigger>
                <Tooltip.Content>
                  <p class="max-w-xs text-xs">Necessario para mensagens em tempo real via WebSocket. Extraido automaticamente do perfil Chatwoot.</p>
                </Tooltip.Content>
              </Tooltip.Root>
            </div>
            <div class="flex items-center gap-2">
              <Input
                id="pubsub_token"
                name="pubsub_token"
                type="text"
                placeholder="Sera preenchido automaticamente"
                value={configValues.pubsub_token || ''}
                class="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5 shrink-0"
                disabled={fetchingPubsub || !isConnected}
                onclick={fetchPubsubToken}
              >
                {#if fetchingPubsub}
                  <Loader2 class="size-3.5 animate-spin" />
                {:else}
                  <Zap class="size-3.5" />
                {/if}
                Buscar Automaticamente
              </Button>
            </div>
            {#if !isConnected}
              <p class="text-amber-600 dark:text-amber-400 text-xs">Salve e conecte primeiro para buscar o token automaticamente.</p>
            {/if}
          </div>

          <!-- Webhook Secret (collapsible) -->
          <details class="rounded-lg border p-3">
            <summary class="cursor-pointer text-sm font-medium text-muted-foreground flex items-center gap-1.5">
              <Shield class="size-3.5" />
              Seguranca Avancada (opcional)
            </summary>
            <div class="mt-3 space-y-2">
              <Label for="webhook_secret">Chave de Seguranca do Webhook</Label>
              <div class="relative">
                <Input
                  id="webhook_secret"
                  name="webhook_secret"
                  type={showWebhookSecret ? 'text' : 'password'}
                  placeholder="HMAC-SHA256 secret (opcional)"
                  value={configValues.webhook_secret || ''}
                  class="pr-10"
                />
                <button
                  type="button"
                  onclick={() => showWebhookSecret = !showWebhookSecret}
                  class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {#if showWebhookSecret}
                    <EyeOff class="size-4" />
                  {:else}
                    <Eye class="size-4" />
                  {/if}
                </button>
              </div>
              <p class="text-muted-foreground text-xs">Para validacao extra dos webhooks. Configure o mesmo valor no Chatwoot.</p>
            </div>
          </details>

          <!-- Buttons -->
          <div class="flex gap-2 pt-2">
            <Button type="submit" variant="outline" class="gap-2">
              <Save class="size-4" />
              Salvar Configuracao
            </Button>
            {#if !integration.is_active}
              <Button type="submit" formaction="?/saveAndConnect" class="gap-2">
                <Wifi class="size-4" />
                Salvar e Conectar
              </Button>
            {/if}
          </div>
        </div>
      </form>
    </Card.Content>
  </Card.Root>

  <!-- ====== Section 3: Webhook URL (prominent) ====== -->
  <Card.Root>
    <Card.Header>
      <Card.Title class="text-base flex items-center gap-2">
        <Webhook class="size-4" />
        Webhook de Eventos
      </Card.Title>
      <Card.Description>URL para receber atualizacoes automaticas do Chatwoot</Card.Description>
    </Card.Header>
    <Card.Content class="space-y-4">
      {#if integration?.webhook_token}
        <div class="space-y-3">
          <Label>URL do Webhook Exclusivo</Label>
          <div class="flex items-center gap-2">
            <div class="bg-muted rounded-md px-3 py-2.5 font-mono text-xs break-all flex-1 border select-all">
              {webhookUrl}
            </div>
            <Button
              variant="outline"
              size="default"
              class="gap-2 shrink-0"
              onclick={copyWebhookUrl}
            >
              {#if webhookCopied}
                <Check class="size-4 text-emerald-500" /> Copiado!
              {:else}
                <Copy class="size-4" /> Copiar URL
              {/if}
            </Button>
          </div>
          <div class="rounded-md border border-green-200 bg-green-50 p-2.5 dark:border-green-800 dark:bg-green-950">
            <p class="text-green-700 dark:text-green-300 text-xs">
              O TalkHub registra o webhook automaticamente ao conectar. Se necessario, copie a URL acima e configure manualmente em:
              <strong>Chatwoot &rarr; Settings &rarr; Integrations &rarr; Webhooks</strong>
            </p>
          </div>
        </div>

        <!-- Webhook events checklist -->
        <div class="space-y-2">
          <p class="text-sm font-medium text-muted-foreground">Eventos monitorados:</p>
          <div class="grid grid-cols-2 gap-1.5 text-xs text-muted-foreground">
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Conversa Criada</span>
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Conversa Atualizada</span>
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Status Alterado</span>
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Mensagem Criada</span>
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Mensagem Atualizada</span>
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Contato Criado</span>
            <span class="flex items-center gap-1"><Check class="size-3 text-emerald-500" /> Contato Atualizado</span>
          </div>
        </div>
      {:else}
        <div class="rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950">
          <p class="text-amber-800 dark:text-amber-200 text-sm">
            <AlertTriangle class="inline size-4 mr-1" />
            Conecte a integracao primeiro para gerar a URL exclusiva do webhook.
          </p>
        </div>
      {/if}
    </Card.Content>
  </Card.Root>

  <!-- ====== Section 4: Sync Behavior ====== -->
  <Card.Root>
    <Card.Header>
      <Card.Title class="text-base flex items-center gap-2">
        <RefreshCw class="size-4" />
        Comportamento da Sincronizacao
      </Card.Title>
    </Card.Header>
    <Card.Content class="space-y-4">
      <!-- Sync Interval -->
      <form method="POST" action="?/saveSyncInterval" use:enhance>
        <div class="flex items-end gap-3">
          <div class="space-y-2 flex-1 max-w-xs">
            <Label>Frequencia de Busca (Fallback)</Label>
            <select name="sync_interval_minutes" class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
              {#each syncIntervalOptions as opt}
                <option value={opt.value} selected={String(integration.sync_interval_minutes) === opt.value}>
                  {opt.label}
                </option>
              {/each}
            </select>
          </div>
          <Button type="submit" variant="outline" class="gap-2" size="sm">
            <Save class="size-4" /> Salvar
          </Button>
        </div>
      </form>

      <Separator />

      <!-- Conflict Strategy -->
      <form method="POST" action="?/saveConflictStrategy" use:enhance>
        <div class="flex items-end gap-3">
          <div class="space-y-2 flex-1 max-w-xs">
            <Label>Resolucao de Conflitos</Label>
            <select name="conflict_strategy" class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
              {#each conflictOptions as opt}
                <option value={opt.value} selected={(integration.conflict_strategy || 'last_write_wins') === opt.value}>
                  {opt.label}
                </option>
              {/each}
            </select>
          </div>
          <Button type="submit" variant="outline" class="gap-2" size="sm">
            <Save class="size-4" /> Salvar
          </Button>
        </div>
      </form>
    </Card.Content>
  </Card.Root>

  <!-- ====== Section 5: Troubleshooting & Health (Collapsible) ====== -->
  <Card.Root>
    <Card.Header>
      <button
        type="button"
        class="flex w-full items-center justify-between text-left"
        onclick={() => showTroubleshooting = !showTroubleshooting}
      >
        <div>
          <Card.Title class="text-base flex items-center gap-2">
            <AlertTriangle class="size-4" />
            Saude da Integracao
          </Card.Title>
          <Card.Description>Diagnostico, logs de falha e reprocessamento</Card.Description>
        </div>
        {#if showTroubleshooting}
          <ChevronUp class="size-5 text-muted-foreground" />
        {:else}
          <ChevronDown class="size-5 text-muted-foreground" />
        {/if}
      </button>
    </Card.Header>

    {#if showTroubleshooting}
      <Card.Content class="space-y-4">
        <!-- Health Status -->
        <div class="flex items-center gap-3 rounded-lg border p-3">
          <IntegrationHealth status={health?.status || 'unknown'} />
          <div class="text-sm">
            <p class="font-medium">Status: {health?.status || 'desconhecido'}</p>
            {#if health?.error_count > 0}
              <p class="text-muted-foreground text-xs">{health.error_count} erro(s) recentes</p>
            {/if}
          </div>
          {#if integration.last_sync_at}
            <div class="ml-auto text-right text-xs text-muted-foreground">
              <p>Ultimo sync bem-sucedido:</p>
              <p class="font-medium">{new Date(integration.last_sync_at).toLocaleString('pt-BR')}</p>
            </div>
          {/if}
        </div>

        <!-- DLQ Table -->
        {#if dlqItems.length > 0}
          <div class="space-y-2">
            <p class="text-sm font-medium">Webhooks com Falha ({dlqItems.length})</p>
            <div class="rounded-lg border overflow-hidden">
              <table class="w-full text-xs">
                <thead class="bg-muted/50">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium">Evento</th>
                    <th class="px-3 py-2 text-left font-medium">Data</th>
                    <th class="px-3 py-2 text-left font-medium">Status</th>
                    <th class="px-3 py-2 text-right font-medium">Acao</th>
                  </tr>
                </thead>
                <tbody class="divide-y">
                  {#each dlqItems as item (item.id)}
                    <tr>
                      <td class="px-3 py-2 font-mono">{item.event_type || '-'}</td>
                      <td class="px-3 py-2 text-muted-foreground">
                        {new Date(item.created_at).toLocaleString('pt-BR')}
                      </td>
                      <td class="px-3 py-2">
                        <Badge variant="destructive" class="text-[10px]">{item.status}</Badge>
                      </td>
                      <td class="px-3 py-2 text-right">
                        {#if item.can_retry !== false}
                          <form method="POST" action="?/reprocessDlq" use:enhance class="inline">
                            <input type="hidden" name="webhook_id" value={item.id} />
                            <Button type="submit" variant="ghost" size="sm" class="gap-1 h-7 text-xs">
                              <RotateCcw class="size-3" /> Reprocessar
                            </Button>
                          </form>
                        {:else}
                          <span class="text-muted-foreground">Nao retentavel</span>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {:else}
          <p class="text-muted-foreground text-sm">Nenhum webhook com falha na fila.</p>
        {/if}

        <!-- Field Mappings -->
        {#if fieldMappings.length > 0}
          <div class="space-y-2">
            <p class="text-sm font-medium">Mapeamento de Campos</p>
            {#each fieldMappings as mapping (mapping.id || mapping.target_field)}
              <div class="bg-muted/50 flex items-center justify-between rounded-lg px-3 py-2 text-xs">
                <span class="font-medium">{mapping.source_field}</span>
                <span class="text-muted-foreground">&rarr;</span>
                <span>{mapping.target_field}</span>
              </div>
            {/each}
          </div>
        {/if}
      </Card.Content>
    {/if}
  </Card.Root>
</div>
