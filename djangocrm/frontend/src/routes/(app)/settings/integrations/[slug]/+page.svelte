<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { ArrowLeft, Plug, RefreshCw, Wifi, WifiOff, Loader2, Clock, Save, AlertTriangle, CircleHelp, Copy, Check } from '@lucide/svelte';
  import IntegrationHealth from '$lib/components/integrations/IntegrationHealth.svelte';
  import ConnectorConfigForm from '$lib/components/integrations/ConnectorConfigForm.svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let integration = $derived(data.integration);
  let health = $derived(data.health);
  let isTesting = $state(false);
  let isSyncing = $state(false);

  /** Whether the integration is connected and active */
  let isConnected = $derived(integration?.is_connected && integration?.is_active);

  /** Whether this is the Chatwoot integration */
  let isChatwoot = $derived(data.slug === 'chatwoot' || integration?.slug === 'chatwoot');

  /** Webhook URL for Chatwoot */
  let chatwootWebhookUrl = $derived(
    typeof window !== 'undefined'
      ? `${window.location.origin}/api/integrations/webhooks/chatwoot/${integration?.webhook_token ? integration.webhook_token + '/' : ''}`
      : `/api/integrations/webhooks/chatwoot/${integration?.webhook_token ? integration.webhook_token + '/' : ''}`
  );

  let webhookCopied = $state(false);
  function copyWebhookUrl() {
    if (typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(chatwootWebhookUrl);
      webhookCopied = true;
      setTimeout(() => { webhookCopied = false; }, 2000);
    }
  }

  /** Whether config has been saved (has non-empty config) */
  let hasConfig = $derived(() => {
    const cfg = integration?.config;
    return cfg && typeof cfg === 'object' && Object.keys(cfg).some(k => cfg[k]);
  });

  $effect(() => {
    if (form?.saved) toast.success('Configuração salva');
    if (form?.connected) toast.success('Integração conectada');
    if (form?.disconnected) toast.success('Integração desconectada');
    if (form?.syncStarted) toast.success('Sincronização iniciada');
    if (form?.syncIntervalSaved) toast.success('Intervalo de sincronização salvo');
    if (form?.error) toast.error(form.error);
    if (form?.testResult) toast.success('Conexão testada: ' + (form.testResult.status || 'OK'));
    if (form?.testError) toast.error(form.testError);
    if (form?.syncError) toast.error(form.syncError);
    if (data.loadError) toast.error(data.loadError);
  });

  /** Config fields derived from integration schema */
  let configFields = $derived(integration?.config_schema?.fields || []);
  let configValues = $derived(integration?.config || {});

  /** Conflict resolution options */
  const conflictOptions = [
    { value: 'last_write_wins', label: 'Última escrita vence' },
    { value: 'crm_wins', label: 'CRM sempre vence' },
    { value: 'external_wins', label: 'Sistema externo vence' },
  ];
</script>

<svelte:head>
  <title>{integration?.name || data.slug} - Integrações - TalkHub CRM</title>
</svelte:head>

<PageHeader title={integration?.name || data.slug} subtitle="Configuração da integração" />

<div class="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
  <Button variant="ghost" href="/settings/integrations" class="gap-2 -ml-2 mb-2" size="sm">
    <ArrowLeft class="size-4" />
    Voltar para Integrações
  </Button>

  {#if data.loadError}
    <Card.Root>
      <Card.Content class="flex flex-col items-center justify-center py-12 text-center">
        <div class="mb-4 flex size-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle class="size-6 text-destructive" />
        </div>
        <p class="text-destructive font-medium">Erro ao carregar integração</p>
        <p class="text-muted-foreground mt-1 text-sm">{data.loadError}</p>
      </Card.Content>
    </Card.Root>
  {:else if !integration}
    <Card.Root>
      <Card.Content class="py-12 text-center">
        <p class="text-muted-foreground">Integração não encontrada.</p>
      </Card.Content>
    </Card.Root>
  {:else}
    <!-- Status & Health -->
    <Card.Root>
      <Card.Header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="flex size-10 items-center justify-center rounded-lg bg-primary/10">
              <Plug class="size-5 text-primary" />
            </div>
            <div>
              <Card.Title>{integration.name}</Card.Title>
              <Card.Description>{integration.slug || data.slug}</Card.Description>
            </div>
          </div>
          <IntegrationHealth status={health?.status || integration.health_status || 'unknown'} />
        </div>
      </Card.Header>
      <Card.Content class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant={integration.is_active ? 'default' : 'secondary'}>
            {integration.is_active ? 'Ativo' : 'Inativo'}
          </Badge>
          <Badge variant={integration.is_connected ? 'default' : 'outline'}>
            {integration.is_connected ? 'Conectado' : 'Desconectado'}
          </Badge>
          {#if isChatwoot}
            <Dialog.Root>
              <Dialog.Trigger>
                <button type="button" class="inline-flex items-center justify-center gap-1.5 rounded-full text-muted-foreground hover:text-foreground transition-colors" title="Como conectar o Chatwoot?">
                  <CircleHelp class="size-5" />
                  <span class="text-xs underline underline-offset-2">Como conectar?</span>
                </button>
              </Dialog.Trigger>
              <Dialog.Content class="max-w-xl max-h-[85vh] overflow-y-auto">
                <Dialog.Header>
                  <Dialog.Title>Como conectar o Chatwoot ao CRM</Dialog.Title>
                  <Dialog.Description>
                    Preencha os dados abaixo e configure o webhook para receber eventos em tempo real.
                  </Dialog.Description>
                </Dialog.Header>
                <div class="space-y-5 text-sm">

                  <!-- Step 1: URL -->
                  <div class="rounded-lg border p-4 space-y-2">
                    <div class="flex items-center gap-2">
                      <span class="flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">1</span>
                      <p class="font-semibold">URL do Chatwoot</p>
                    </div>
                    <p class="text-muted-foreground">
                      É o endereço que você usa para acessar o painel do Chatwoot. Exemplo:
                    </p>
                    <div class="bg-muted rounded-md px-3 py-2 font-mono text-xs">
                      https://chat.seudominio.com.br
                    </div>
                  </div>

                  <!-- Step 2: Account ID -->
                  <div class="rounded-lg border p-4 space-y-2">
                    <div class="flex items-center gap-2">
                      <span class="flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">2</span>
                      <p class="font-semibold">ID da Conta (Account ID)</p>
                    </div>
                    <p class="text-muted-foreground">
                      No Chatwoot, vá em <strong>Settings &rarr; Account Settings</strong>. O ID aparece na URL do navegador:
                    </p>
                    <div class="bg-muted rounded-md px-3 py-2 font-mono text-xs">
                      https://chat.seudominio.com.br/app/accounts/<strong class="text-foreground">1</strong>/settings/general
                    </div>
                    <p class="text-muted-foreground text-xs">
                      O número após <code>/accounts/</code> é o seu Account ID.
                    </p>
                  </div>

                  <!-- Step 3: Token -->
                  <div class="rounded-lg border p-4 space-y-2">
                    <div class="flex items-center gap-2">
                      <span class="flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">3</span>
                      <p class="font-semibold">Token de Acesso (API Access Token)</p>
                    </div>
                    <p class="text-muted-foreground">
                      No Chatwoot, clique no seu <strong>avatar</strong> (canto inferior esquerdo) e depois em:
                    </p>
                    <div class="flex items-center gap-2 text-muted-foreground">
                      <span class="bg-muted rounded px-2 py-1 font-mono text-xs">Profile Settings</span>
                      <span>&rarr;</span>
                      <span class="bg-muted rounded px-2 py-1 font-mono text-xs">Access Token</span>
                    </div>
                    <p class="text-muted-foreground text-xs">
                      Copie o token exibido. Se não existir, clique em "Create" para gerar um novo.
                    </p>
                  </div>

                  <!-- Step 4: Webhook -->
                  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3 dark:border-blue-800 dark:bg-blue-950">
                    <div class="flex items-center gap-2">
                      <span class="flex size-6 items-center justify-center rounded-full bg-blue-600 text-white text-xs font-bold">4</span>
                      <p class="font-semibold text-blue-800 dark:text-blue-200">Configurar Webhook no Chatwoot</p>
                    </div>
                    <p class="text-blue-700 dark:text-blue-300">
                      No Chatwoot, vá em <strong>Settings &rarr; Integrations &rarr; Webhook &rarr; Adicionar novo webhook</strong>
                      e cole a URL abaixo:
                    </p>
                    {#if integration?.webhook_token}
                    <div class="flex items-center gap-2">
                      <div class="bg-white dark:bg-blue-900 rounded-md px-3 py-2 font-mono text-xs break-all flex-1 border border-blue-200 dark:border-blue-700 select-all">
                        {chatwootWebhookUrl}
                      </div>
                      <button
                        type="button"
                        onclick={copyWebhookUrl}
                        class="shrink-0 rounded-md border border-blue-200 dark:border-blue-700 bg-white dark:bg-blue-900 p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
                        title="Copiar URL"
                      >
                        {#if webhookCopied}
                          <Check class="size-4" />
                        {:else}
                          <Copy class="size-4" />
                        {/if}
                      </button>
                    </div>
                    {:else}
                    <p class="text-amber-600 dark:text-amber-400 text-xs font-medium">
                      Conecte a integração primeiro para gerar a URL exclusiva do webhook.
                    </p>
                    {/if}
                    <p class="text-blue-700 dark:text-blue-300">
                      Marque os seguintes eventos:
                    </p>
                    <div class="grid grid-cols-2 gap-1 text-xs text-blue-600 dark:text-blue-400">
                      <span>&#x2713; Conversa Criada</span>
                      <span>&#x2713; Conversa Atualizada</span>
                      <span>&#x2713; Status de conversa alterado</span>
                      <span>&#x2713; Mensagem criada</span>
                      <span>&#x2713; Mensagem atualizada</span>
                      <span>&#x2713; Contato criado</span>
                      <span>&#x2713; Contato atualizado</span>
                    </div>
                    <p class="text-blue-600 dark:text-blue-400 text-xs">
                      O webhook permite que o CRM receba atualizações em tempo real do Chatwoot, sem necessidade de polling.
                    </p>
                  </div>

                  <!-- Webhook auto-register info -->
                  <div class="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-950">
                    <p class="text-green-700 dark:text-green-300 text-xs">
                      <strong>Dica:</strong> Ao clicar em "Salvar e Conectar", o CRM tenta registrar o webhook automaticamente via API.
                      Se o registro automático falhar (por permissões ou rede), configure manualmente pelo passo 4 acima.
                    </p>
                  </div>

                  <!-- Webhook Secret (optional) -->
                  <div class="rounded-lg border border-dashed p-4 space-y-2">
                    <p class="font-semibold text-muted-foreground">Webhook Secret (opcional)</p>
                    <p class="text-muted-foreground text-xs">
                      Para validar a autenticidade dos webhooks, defina um secret aqui e configure o mesmo valor
                      no Chatwoot ao editar o webhook. Recomendado para produção, mas não obrigatório.
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
          {/if}
          {#if integration.last_sync_at}
            <span class="text-muted-foreground text-xs">
              Último sync: {new Date(integration.last_sync_at).toLocaleString('pt-BR')}
            </span>
          {/if}
        </div>

        {#if !isConnected && configFields.length > 0}
          <div class="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <p>Configure as credenciais abaixo e clique em "Salvar e Conectar" para ativar esta integração.</p>
          </div>
        {/if}

        <Separator />

        <div class="flex flex-wrap gap-2">
          <form method="POST" action="?/testConnection" use:enhance={() => {
            isTesting = true;
            return async ({ update }) => { isTesting = false; await update(); };
          }}>
            <Button variant="outline" type="submit" disabled={isTesting || !isConnected} class="gap-2" size="sm">
              <Wifi class="size-4" />
              {isTesting ? 'Testando...' : 'Testar Conexão'}
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
          {:else}
            <form method="POST" action="?/connect" use:enhance>
              <Button variant="outline" type="submit" class="gap-2" size="sm">
                <Wifi class="size-4" />
                Conectar
              </Button>
            </form>
          {/if}
        </div>
      </Card.Content>
    </Card.Root>

    <!-- Connector Config -->
    {#if configFields.length > 0}
      <Card.Root>
        <Card.Header>
          <Card.Title class="text-base">Configuração do Conector</Card.Title>
          <Card.Description>Insira as credenciais e configurações necessárias</Card.Description>
        </Card.Header>
        <Card.Content>
          <ConnectorConfigForm fields={configFields} values={configValues} showConnect={!integration.is_active} />
        </Card.Content>
      </Card.Root>
    {/if}

    <!-- Sync Interval -->
    <Card.Root>
      <Card.Header>
        <Card.Title class="text-base">Agendamento de Sincronização</Card.Title>
        <Card.Description>Configure o intervalo entre sincronizações automáticas (5 a 1440 minutos)</Card.Description>
      </Card.Header>
      <Card.Content>
        <form method="POST" action="?/saveSyncInterval" use:enhance>
          <div class="flex items-end gap-3">
            <div class="space-y-2">
              <Label for="sync_interval_minutes">Intervalo (minutos)</Label>
              <Input
                id="sync_interval_minutes"
                name="sync_interval_minutes"
                type="number"
                min="5"
                max="1440"
                value={integration.sync_interval_minutes ?? 60}
                class="w-40"
                required
              />
            </div>
            <Button type="submit" variant="outline" class="gap-2" size="sm">
              <Clock class="size-4" />
              Salvar Intervalo
            </Button>
          </div>
        </form>
      </Card.Content>
    </Card.Root>

    <!-- Conflict Resolution -->
    <Card.Root>
      <Card.Header>
        <Card.Title class="text-base">Resolução de Conflitos</Card.Title>
        <Card.Description>Defina como conflitos de dados são resolvidos durante a sincronização</Card.Description>
      </Card.Header>
      <Card.Content>
        <form method="POST" action="?/saveConflictStrategy" use:enhance>
          <div class="flex items-end gap-3">
            <div class="space-y-2 flex-1 max-w-xs">
              <Label for="conflict_strategy">Estratégia</Label>
              <Select.Root type="single" name="conflict_strategy" value={integration.conflict_strategy || 'last_write_wins'}>
                <Select.Trigger class="w-full">
                  {conflictOptions.find(o => o.value === (integration.conflict_strategy || 'last_write_wins'))?.label || 'Selecione...'}
                </Select.Trigger>
                <Select.Content>
                  {#each conflictOptions as opt}
                    <Select.Item value={opt.value}>{opt.label}</Select.Item>
                  {/each}
                </Select.Content>
              </Select.Root>
            </div>
            <Button type="submit" variant="outline" class="gap-2" size="sm">
              <Save class="size-4" />
              Salvar
            </Button>
          </div>
        </form>
      </Card.Content>
    </Card.Root>

    <!-- Field Mappings -->
    <Card.Root>
      <Card.Header>
        <Card.Title class="text-base">Mapeamento de Campos</Card.Title>
        <Card.Description>Configure como os campos são mapeados entre os sistemas</Card.Description>
      </Card.Header>
      <Card.Content>
        {#if data.fieldMappings.length > 0}
          <div class="space-y-2">
            {#each data.fieldMappings as mapping (mapping.id || mapping.target_field)}
              <div class="bg-muted/50 flex items-center justify-between rounded-lg px-3 py-2 text-sm">
                <span class="font-medium">{mapping.target_field}</span>
                <span class="text-muted-foreground">→</span>
                <span>{mapping.source_field}</span>
                <Badge variant="outline" class="text-xs">{mapping.direction || 'bidirectional'}</Badge>
              </div>
            {/each}
          </div>
        {:else}
          <p class="text-muted-foreground text-sm">Nenhum mapeamento configurado.</p>
        {/if}
      </Card.Content>
    </Card.Root>
  {/if}
</div>
