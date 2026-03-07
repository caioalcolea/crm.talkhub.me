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
  import { MessageSquare, ExternalLink, Trash2, RefreshCw, Key, BarChart3, Layers } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let thStatus = $derived(data.thStatus || { connected: false });
  let isConnecting = $state(false);
  let isDisconnecting = $state(false);
  let disconnectDialogOpen = $state(false);

  $effect(() => {
    if (form?.connected) toast.success('TalkHub Omni conectado com sucesso');
    if (form?.disconnected) toast.success('TalkHub Omni desconectado');
    if (form?.credentialError) toast.error(form.credentialError);
    if (data.error) toast.error(data.error);
  });

  /**
   * @param {string} dateStr
   */
  function formatDate(dateStr) {
    if (!dateStr) return 'Desconhecido';
    try {
      return new Date(dateStr).toLocaleDateString('pt-BR', {
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
  <title>Integração TalkHub Omni - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Integração TalkHub Omni" subtitle="Conecte e sincronize dados do TalkHub Omni" />

<div class="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
  {#if thStatus.connected}
    <!-- CONNECTED STATE -->
    <Card.Root>
      <Card.Header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="flex size-10 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-950">
              <MessageSquare class="size-5 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <Card.Title>Conexão TalkHub Omni</Card.Title>
              <Card.Description>Sua plataforma omnichannel está conectada</Card.Description>
            </div>
          </div>
          <Badge class="border-emerald-200 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">
            Conectado
          </Badge>
        </div>
      </Card.Header>
      <Card.Content>
        <div class="space-y-4">
          <div class="bg-muted/50 rounded-lg p-4">
            <dl class="grid gap-3 sm:grid-cols-2">
              {#if thStatus.workspace_name}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Workspace</dt>
                  <dd class="text-foreground mt-1 text-sm">{thStatus.workspace_name}</dd>
                </div>
              {/if}
              {#if thStatus.workspace_url}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">URL</dt>
                  <dd class="text-foreground mt-1 text-sm">
                    <a
                      href={thStatus.workspace_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex items-center gap-1 text-violet-600 hover:underline dark:text-violet-400"
                    >
                      {thStatus.workspace_url}
                      <ExternalLink class="size-3" />
                    </a>
                  </dd>
                </div>
              {/if}
              {#if thStatus.owner_email}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Owner</dt>
                  <dd class="text-foreground mt-1 text-sm">{thStatus.owner_email}</dd>
                </div>
              {/if}
              {#if thStatus.connected_by_email}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Conectado por</dt>
                  <dd class="text-foreground mt-1 text-sm">{thStatus.connected_by_email}</dd>
                </div>
              {/if}
              {#if thStatus.last_sync_at}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Último sync</dt>
                  <dd class="text-foreground mt-1 text-sm">{formatDate(thStatus.last_sync_at)}</dd>
                </div>
              {/if}
              {#if thStatus.connected_at}
                <div>
                  <dt class="text-muted-foreground text-sm font-medium">Conectado em</dt>
                  <dd class="text-foreground mt-1 text-sm">{formatDate(thStatus.connected_at)}</dd>
                </div>
              {/if}
            </dl>
          </div>

          <Separator />

          <div class="flex flex-wrap items-center gap-2">
            <Button variant="outline" href="/settings/talkhub-omni/sync" class="gap-2">
              <RefreshCw class="size-4" />
              Sincronizar Dados
            </Button>
            <Button variant="outline" href="/settings/talkhub-omni/analytics" class="gap-2">
              <BarChart3 class="size-4" />
              Analytics
            </Button>
            <Button variant="outline" href="/settings/talkhub-omni/channels" class="gap-2">
              <Layers class="size-4" />
              Canais
            </Button>
            <div class="flex-1"></div>
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
    <!-- NOT CONNECTED STATE -->
    <Card.Root>
      <Card.Header class="text-center">
        <div class="mx-auto mb-4 flex size-16 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-950">
          <Key class="size-8 text-violet-600 dark:text-violet-400" />
        </div>
        <Card.Title class="text-xl">Conectar ao TalkHub Omni</Card.Title>
        <Card.Description class="mx-auto max-w-md">
          Insira a API Key do seu workspace TalkHub Omni para sincronizar contatos, kanban, tags, analytics e muito mais.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        <div class="space-y-6">
          <div class="bg-muted/50 rounded-lg p-4">
            <h4 class="text-foreground mb-3 text-sm font-medium">Como obter sua API Key:</h4>
            <ol class="text-muted-foreground space-y-2 text-sm">
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">1.</span>
                <span>Acesse seu painel <strong class="text-foreground">TalkHub Omni</strong></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">2.</span>
                <span>Vá para <strong class="text-foreground">Settings</strong> &rarr; <strong class="text-foreground">Developer API</strong></span>
              </li>
              <li class="flex gap-2">
                <span class="text-foreground shrink-0 font-medium">3.</span>
                <span>Copie a <strong class="text-foreground">API Key</strong> e cole abaixo</span>
              </li>
            </ol>
          </div>

          <Separator />

          <form method="POST" action="?/saveCredentials" use:enhance={() => {
            isConnecting = true;
            return async ({ update }) => {
              isConnecting = false;
              await update();
            };
          }}>
            <div class="space-y-4">
              <div class="space-y-2">
                <Label for="workspace_url">URL do Workspace</Label>
                <Input
                  id="workspace_url"
                  name="workspace_url"
                  type="url"
                  placeholder="https://chat.talkhub.me"
                  value="https://chat.talkhub.me"
                  autocomplete="off"
                />
                <p class="text-muted-foreground text-xs">
                  URL base do seu workspace TalkHub Omni (padrão: <code class="bg-muted rounded px-1">https://chat.talkhub.me</code>)
                </p>
              </div>
              <div class="space-y-2">
                <Label for="api_key">API Key</Label>
                <Input
                  id="api_key"
                  name="api_key"
                  type="password"
                  placeholder="Insira sua API Key do TalkHub Omni"
                  required
                  autocomplete="off"
                />
              </div>
              <Button
                type="submit"
                disabled={isConnecting}
                class="w-full gap-2 border-0 bg-[var(--color-primary-default)] text-white hover:bg-[var(--color-primary-hover)]"
              >
                <MessageSquare class="size-4" />
                {isConnecting ? 'Conectando ao TalkHub Omni...' : 'Conectar ao TalkHub Omni'}
              </Button>
            </div>
          </form>
        </div>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Header>
        <Card.Title class="text-base">O que é sincronizado?</Card.Title>
      </Card.Header>
      <Card.Content>
        <ul class="text-muted-foreground space-y-2 text-sm">
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Contatos</strong> - Subscribers ↔ Contatos CRM (bidirecional)</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Kanban</strong> - Ticket Lists ↔ Boards CRM</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Tags</strong> - Tags e labels sincronizadas</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Usuários</strong> - Team members importados</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Analytics</strong> - Métricas de conversas e atendimento</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Bot Control</strong> - Pause/resume de bots por contato</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="mt-1.5 size-1.5 shrink-0 rounded-full bg-violet-500"></span>
            <span><strong class="text-foreground">Canais</strong> - WhatsApp, Instagram, Messenger e mais</span>
          </li>
        </ul>
      </Card.Content>
    </Card.Root>
  {/if}
</div>

<!-- Disconnect Dialog -->
<Dialog.Root bind:open={disconnectDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Desconectar TalkHub Omni</Dialog.Title>
      <Dialog.Description>
        Tem certeza que deseja desconectar do TalkHub Omni? Os dados importados anteriormente não serão excluídos.
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
