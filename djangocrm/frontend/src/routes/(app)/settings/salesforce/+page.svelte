<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import { PageHeader } from '$lib/components/layout';
  import { Cloud, ExternalLink, Trash2, Download, Key } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let sfStatus = $derived(data.sfStatus || { connected: false });
  let isConnecting = $state(false);
  let isDisconnecting = $state(false);
  let disconnectDialogOpen = $state(false);

  // Show toast for form results
  $effect(() => {
    if (form?.connected) toast.success('Salesforce conectado com sucesso');
    if (form?.disconnected) toast.success('Salesforce desconectado');
    if (form?.credentialError) toast.error(form.credentialError);
    if (data.error) toast.error(data.error);
  });

  /**
   * Format a date string for display
   * @param {string} dateStr
   */
  function formatDate(dateStr) {
    if (!dateStr) return 'Desconhecido';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  }
</script>

<svelte:head>
  <title>Integração Salesforce - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Integração Salesforce" subtitle="Conecte e importe dados do Salesforce" />

<div class="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
  {#if sfStatus.connected}
    <!-- ============================================================ -->
    <!-- CONNECTED -->
    <!-- ============================================================ -->
    <Card.Root>
      <Card.Header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div
              class="flex size-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950"
            >
              <Cloud class="size-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <Card.Title>Conexão Salesforce</Card.Title>
              <Card.Description>Sua organização Salesforce está conectada</Card.Description>
            </div>
          </div>
          <Badge
            class="border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400"
          >
            Conectado
          </Badge>
        </div>
      </Card.Header>
      <Card.Content>
        <div class="space-y-4">
          <div class="bg-muted/50 rounded-lg p-4">
            <dl class="grid gap-3 sm:grid-cols-2">
              {#if sfStatus.connection?.instance_url}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">URL da Instância</dt>
                  <dd class="text-foreground mt-1 text-sm">
                    <a
                      href={sfStatus.connection.instance_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400"
                    >
                      {sfStatus.connection.instance_url}
                      <ExternalLink class="size-3" />
                    </a>
                  </dd>
                </div>
              {/if}
              {#if sfStatus.connection?.connected_by_email}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Conectado por</dt>
                  <dd class="text-foreground mt-1 text-sm">{sfStatus.connection.connected_by_email}</dd>
                </div>
              {/if}
              {#if sfStatus.connection?.created_at}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Conectado em</dt>
                  <dd class="text-foreground mt-1 text-sm">{formatDate(sfStatus.connection.created_at)}</dd>
                </div>
              {/if}
            </dl>
          </div>

          <Separator />

          <div class="flex items-center justify-between">
            <Button variant="outline" href="/settings/salesforce/import" class="gap-2">
              <Download class="size-4" />
              Importar Dados
            </Button>
            <Button
              variant="outline"
              class="text-destructive hover:bg-destructive/10 gap-2"
              onclick={() => (disconnectDialogOpen = true)}
              type="button"
            >
              <Trash2 class="size-4" />
              Desconectar
            </Button>
          </div>
        </div>
      </Card.Content>
    </Card.Root>
  {:else}
    <!-- ============================================================ -->
    <!-- NOT CONNECTED - Setup + Credential Form -->
    <!-- ============================================================ -->
    <Card.Root>
      <Card.Header class="text-center">
        <div
          class="mx-auto mb-4 flex size-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950"
        >
          <Key class="size-8 text-blue-600 dark:text-blue-400" />
        </div>
        <Card.Title class="text-xl">Conectar ao Salesforce</Card.Title>
        <Card.Description class="mx-auto max-w-md">
          Crie um Aplicativo Conectado na sua organização Salesforce e insira as credenciais abaixo para conectar.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        <div class="space-y-6">
          <!-- Setup instructions -->
          <div class="bg-muted/50 rounded-lg p-4">
            <h4 class="text-foreground mb-3 text-sm font-medium">Como criar um Aplicativo Conectado:</h4>
            <ol class="text-muted-foreground space-y-2 text-sm">
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">1.</span>
                <span>Faça login no <strong class="text-foreground">Salesforce Setup</strong></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">2.</span>
                <span>Vá para <strong class="text-foreground">App Manager</strong> &rarr; <strong class="text-foreground">New Connected App</strong></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">3.</span>
                <span>Habilite <strong class="text-foreground">OAuth Settings</strong> e defina a URL de Callback para <code class="bg-muted rounded px-1 text-xs">https://login.salesforce.com/services/oauth2/success</code></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">4.</span>
                <span>Adicione os escopos OAuth: <code class="bg-muted rounded px-1 text-xs">api</code>, <code class="bg-muted rounded px-1 text-xs">refresh_token</code></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">5.</span>
                <span>Marque <strong class="text-foreground">Enable Client Credentials Flow</strong></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">6.</span>
                <span>Atribua um usuário <strong class="text-foreground">Run As</strong> ao Aplicativo Conectado (necessário para Client Credentials)</span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">7.</span>
                <span>Copie a <strong class="text-foreground">Consumer Key</strong> (Client ID) e o <strong class="text-foreground">Consumer Secret</strong> (Client Secret) abaixo</span>
              </li>
            </ol>
          </div>

          <Separator />

          <!-- Credential form - saves + connects in one step -->
          <form method="POST" action="?/saveCredentials" use:enhance={() => {
            isConnecting = true;
            return async ({ update }) => {
              isConnecting = false;
              await update();
            };
          }}>
            <div class="space-y-4">
              <div class="space-y-2">
                <Label for="login_url">URL do My Domain do Salesforce</Label>
                <Input
                  id="login_url"
                  name="login_url"
                  type="url"
                  placeholder="https://yourcompany.my.salesforce.com"
                  required
                  autocomplete="off"
                />
                <p class="text-muted-foreground text-xs">
                  Encontre em Salesforce Setup &rarr; My Domain. Use <code class="bg-muted rounded px-1">https://suaempresa.my.salesforce.com</code>
                </p>
              </div>
              <div class="space-y-2">
                <Label for="client_id">Client ID (Consumer Key)</Label>
                <Input
                  id="client_id"
                  name="client_id"
                  type="text"
                  placeholder="3MVG9..."
                  required
                  autocomplete="off"
                />
              </div>
              <div class="space-y-2">
                <Label for="client_secret">Client Secret (Consumer Secret)</Label>
                <Input
                  id="client_secret"
                  name="client_secret"
                  type="password"
                  placeholder="Insira seu client secret"
                  required
                  autocomplete="off"
                />
              </div>
              <Button
                type="submit"
                disabled={isConnecting}
                class="w-full gap-2 border-0 bg-[var(--color-primary-default)] text-white hover:bg-[var(--color-primary-hover)]"
              >
                <Cloud class="size-4" />
                {isConnecting ? 'Conectando ao Salesforce...' : 'Conectar ao Salesforce'}
              </Button>
            </div>
          </form>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Header>
        <Card.Title class="text-base">O que é importado?</Card.Title>
      </Card.Header>
      <Card.Content>
        <ul class="text-muted-foreground space-y-2 text-sm">
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span
              ><strong class="text-foreground">Contas</strong> - Empresas e organizações</span
            >
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span
              ><strong class="text-foreground">Contatos</strong> - Pessoas associadas às contas</span
            >
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span
              ><strong class="text-foreground">Oportunidades</strong> - Negócios e pipeline de vendas</span
            >
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span><strong class="text-foreground">Produtos</strong> - Catálogo de produtos</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span><strong class="text-foreground">Pedidos</strong> - Pedidos de venda</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-blue-500"></span>
            <span><strong class="text-foreground">Cotações</strong> - Cotações e orçamentos</span
            >
          </li>
        </ul>
      </Card.Content>
    </Card.Root>
  {/if}
</div>

<!-- Disconnect Confirmation Dialog -->
<Dialog.Root bind:open={disconnectDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Desconectar Salesforce</Dialog.Title>
      <Dialog.Description>
        Tem certeza que deseja desconectar do Salesforce? Os dados importados anteriormente não serão excluídos.
      </Dialog.Description>
    </Dialog.Header>
    <form method="POST" action="?/disconnect" use:enhance={() => {
      isDisconnecting = true;
      return async ({ update }) => {
        isDisconnecting = false;
        disconnectDialogOpen = false;
        await update();
      };
    }}>
      <div class="flex justify-end gap-2 pt-4">
        <Button variant="outline" type="button" onclick={() => (disconnectDialogOpen = false)}>Cancelar</Button>
        <Button variant="destructive" type="submit" disabled={isDisconnecting}>
          {isDisconnecting ? 'Desconectando...' : 'Desconectar'}
        </Button>
      </div>
    </form>
  </Dialog.Content>
</Dialog.Root>
