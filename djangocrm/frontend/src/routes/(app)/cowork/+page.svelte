<script>
  import { enhance } from '$app/forms';
  import { onDestroy } from 'svelte';
  import { toast } from 'svelte-sonner';
  import { PageHeader } from '$lib/components/layout';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import {
    Plus, Video, Users, Link, Trash2, Play, Copy, UserPlus,
    Maximize, Minimize, LogOut, Wifi, WifiOff, Monitor
  } from '@lucide/svelte';

  const COWORK_APP_URL = '/cowork-app/';
  const COWORK_SOCKET_URL = `${typeof window !== 'undefined' ? window.location.origin : ''}/cowork-ws`;

  let { data, form } = $props();

  let rooms = $derived(data.rooms || []);
  let selectedRoom = $state(null);
  let coworkToken = $state(null);
  let showCreateRoom = $state(false);
  let showInvite = $state(false);
  let inviteRoom = $state(null);
  let inviteResult = $state(null);
  let iframeRef = $state(null);
  let containerRef = $state(null);
  let iframeReady = $state(false);
  let isFullscreen = $state(false);

  $effect(() => {
    if (form?.toast) toast.success(form.toast);
    if (form?.error) toast.error(form.error);
    if (form?.coworkToken) {
      coworkToken = form.coworkToken;
      selectedRoom = form.room;
      iframeReady = false;
    }
    if (form?.invite) {
      inviteResult = form.invite;
    }
  });

  // Listen for postMessage from cowork-app iframe
  function handleMessage(event) {
    const { type, payload } = event.data || {};
    switch (type) {
      case 'cowork-ready':
        iframeReady = true;
        if (iframeRef?.contentWindow && coworkToken && selectedRoom) {
          iframeRef.contentWindow.postMessage({
            type: 'cowork-init',
            payload: {
              socketUrl: COWORK_SOCKET_URL,
              token: coworkToken,
              roomId: selectedRoom.id,
              displayName: data.user?.name || data.user?.email || 'User',
              isGuest: false
            }
          }, '*');
        }
        break;
      case 'cowork-status':
        break;
      case 'cowork-error':
        toast.error(payload?.message || 'Erro no cowork');
        break;
    }
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('message', handleMessage);
    document.addEventListener('fullscreenchange', onFullscreenChange);
  }
  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('message', handleMessage);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    }
    if (iframeRef?.contentWindow) {
      iframeRef.contentWindow.postMessage({ type: 'cowork-destroy' }, '*');
    }
  });

  function leaveRoom() {
    if (iframeRef?.contentWindow) {
      iframeRef.contentWindow.postMessage({ type: 'cowork-destroy' }, '*');
    }
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    coworkToken = null;
    selectedRoom = null;
    iframeReady = false;
  }

  function onFullscreenChange() {
    isFullscreen = !!document.fullscreenElement;
  }

  function toggleFullscreen() {
    if (!containerRef) return;
    if (!document.fullscreenElement) {
      containerRef.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }

  function copyInviteLink() {
    if (inviteResult?.invite_url) {
      navigator.clipboard.writeText(inviteResult.invite_url);
      toast.success('Link copiado!');
    }
  }

  function enterRoom(roomId) {
    const form = document.getElementById('enter-room-form');
    if (form) {
      const input = form.querySelector('input[name="room_id"]');
      if (input) input.value = roomId;
      form.requestSubmit();
    }
  }

  function openInviteDialog(room) {
    inviteRoom = room;
    inviteResult = null;
    showInvite = true;
  }
</script>

<svelte:head>
  <title>Sala Cowork | TalkHub CRM</title>
</svelte:head>

<!-- Hidden form for entering rooms -->
<form id="enter-room-form" method="POST" action="?/getToken" use:enhance class="hidden">
  <input type="hidden" name="room_id" value="" />
</form>

<div class="flex flex-col">
  <!-- Page Header (standard CRM pattern) -->
  <PageHeader title="Sala Cowork" subtitle="Escritório virtual">
    {#snippet actions()}
      <div class="flex items-center gap-2">
        {#if coworkToken && selectedRoom}
          <Button variant="outline" size="sm" onclick={toggleFullscreen} class="gap-2">
            {#if isFullscreen}
              <Minimize class="size-4" />
              <span class="hidden sm:inline">Sair Fullscreen</span>
            {:else}
              <Maximize class="size-4" />
              <span class="hidden sm:inline">Fullscreen</span>
            {/if}
          </Button>
          <Button variant="outline" size="sm" onclick={leaveRoom} class="gap-2">
            <LogOut class="size-4" />
            <span class="hidden sm:inline">Sair da Sala</span>
          </Button>
        {/if}
        <Button onclick={() => showCreateRoom = true} class="gap-2">
          <Plus class="size-4" />
          Nova Sala
        </Button>
      </div>
    {/snippet}
  </PageHeader>

  <!-- Active cowork session -->
  {#if coworkToken && selectedRoom}
    <div bind:this={containerRef} class="flex flex-col" class:fullscreen-container={isFullscreen}>
      <!-- Session toolbar -->
      <div class="flex items-center justify-between border-b border-[var(--border-default)] bg-[var(--surface-raised)] px-4 py-2.5 md:px-6">
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium
            {iframeReady
              ? 'bg-[var(--task-completed-bg)] text-[var(--task-completed)] dark:bg-[var(--task-completed)]/15'
              : 'bg-[var(--task-due-today-bg)] text-[var(--task-due-today)] dark:bg-[var(--task-due-today)]/15'
            }">
            {#if iframeReady}
              <Wifi class="size-3" />
              Ao Vivo
            {:else}
              <WifiOff class="size-3 animate-pulse" />
              Conectando...
            {/if}
          </div>
          <span class="text-sm font-semibold text-[var(--text-primary)]">{selectedRoom.name}</span>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="ghost" size="sm" onclick={() => openInviteDialog(selectedRoom)} class="gap-1.5 text-[var(--text-secondary)]">
            <UserPlus class="size-3.5" />
            <span class="hidden sm:inline">Convidar</span>
          </Button>
          {#if isFullscreen}
            <Button variant="outline" size="sm" onclick={toggleFullscreen} class="gap-1.5">
              <Minimize class="size-3.5" />
              <span class="hidden sm:inline">Sair Fullscreen</span>
            </Button>
          {/if}
          <Button variant="outline" size="sm" onclick={leaveRoom} class="gap-1.5">
            <LogOut class="size-3.5" />
            <span class="hidden sm:inline">Sair</span>
          </Button>
        </div>
      </div>

      <!-- Iframe wrapper -->
      <div class="relative flex-1 bg-[var(--surface-sunken)]" class:iframe-fullscreen={isFullscreen} style={isFullscreen ? '' : 'height: calc(100vh - 12rem);'}>
        <iframe
          bind:this={iframeRef}
          src={COWORK_APP_URL}
          title="Sala Cowork"
          class="h-full w-full border-0"
          allow="camera; microphone; display-capture"
          sandbox="allow-scripts allow-same-origin allow-popups"
        ></iframe>
        {#if !iframeReady}
          <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[var(--surface-default)]">
            <div class="flex size-14 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary-light)] dark:bg-[var(--color-primary-default)]/15">
              <Monitor class="size-7 text-[var(--color-primary-default)] animate-pulse" />
            </div>
            <div class="text-center">
              <p class="text-sm font-semibold text-[var(--text-primary)]">Carregando escritório virtual...</p>
              <p class="mt-1 text-xs text-[var(--text-tertiary)]">Conectando ao servidor de cowork</p>
            </div>
            <div class="mt-2 h-1 w-48 overflow-hidden rounded-full bg-[var(--surface-sunken)]">
              <div class="loading-bar h-full rounded-full bg-[var(--color-primary-default)]"></div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <!-- Room list -->
    <div class="space-y-6 px-6 py-6 md:px-8">
      {#if rooms.length === 0}
        <!-- Empty state (standard CRM pattern) -->
        <div class="flex flex-col items-center justify-center rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] py-16 text-center">
          <div class="mb-4 flex size-16 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--surface-sunken)]">
            <Video class="size-8 text-[var(--text-tertiary)]" strokeWidth={1.5} />
          </div>
          <h3 class="text-lg font-medium text-[var(--text-primary)]">Nenhuma sala criada</h3>
          <p class="mb-4 text-sm text-[var(--text-secondary)]">
            Crie sua primeira sala virtual para começar.
          </p>
          <Button onclick={() => showCreateRoom = true} class="gap-2">
            <Plus class="size-4" />
            Criar Sala
          </Button>
        </div>
      {:else}
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {#each rooms as room (room.id)}
            <div class="group rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--surface-raised)] p-5 shadow-[var(--shadow-xs)] transition-all duration-150 hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-sm)] dark:bg-[var(--surface-raised)]/80">
              <!-- Room header -->
              <div class="mb-4 flex items-start justify-between">
                <div class="flex items-center gap-3">
                  <div class="flex size-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary-light)] dark:bg-[var(--color-primary-default)]/15">
                    <Video class="size-5 text-[var(--color-primary-default)]" />
                  </div>
                  <div>
                    <h3 class="font-semibold text-[var(--text-primary)]">{room.name}</h3>
                    <p class="text-xs text-[var(--text-tertiary)]">Escritório virtual</p>
                  </div>
                </div>
                <div class="flex items-center gap-1.5 rounded-full bg-[var(--surface-sunken)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)]">
                  <Users class="size-3" />
                  {room.participant_count || 0}/{room.max_participants}
                </div>
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-2">
                <Button
                  size="sm"
                  class="flex-1 gap-1.5"
                  onclick={() => enterRoom(room.id)}
                >
                  <Play class="size-3.5" />
                  Entrar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onclick={() => openInviteDialog(room)}
                  title="Convidar visitante"
                >
                  <UserPlus class="size-3.5" />
                </Button>
                <form method="POST" action="?/deleteRoom" use:enhance>
                  <input type="hidden" name="id" value={room.id} />
                  <Button
                    type="submit"
                    size="sm"
                    variant="ghost"
                    class="text-[var(--color-negative-default)] hover:text-[var(--color-negative-default)] hover:bg-[var(--color-negative-light)]"
                    title="Excluir sala"
                  >
                    <Trash2 class="size-3.5" />
                  </Button>
                </form>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Create Room Dialog -->
<Dialog.Root bind:open={showCreateRoom}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Nova Sala Cowork</Dialog.Title>
      <Dialog.Description>Crie uma sala virtual para sua equipe.</Dialog.Description>
    </Dialog.Header>
    <form method="POST" action="?/createRoom" use:enhance={() => {
      return async ({ update }) => {
        await update();
        showCreateRoom = false;
      };
    }}>
      <div class="space-y-4 py-4">
        <div>
          <label for="room-name" class="text-sm font-medium text-[var(--text-primary)]">Nome da Sala</label>
          <input
            id="room-name"
            name="name"
            type="text"
            required
            placeholder="Ex: Escritório Principal"
            class="mt-1.5 flex h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-transparent px-3 py-1 text-sm shadow-[var(--shadow-xs)] transition-colors placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary-default)]"
          />
        </div>
        <input type="hidden" name="map_id" value="office_default" />
        <div>
          <label for="room-max" class="text-sm font-medium text-[var(--text-primary)]">Máx. Participantes</label>
          <input
            id="room-max"
            name="max_participants"
            type="number"
            min="2"
            max="50"
            value="25"
            class="mt-1.5 flex h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-transparent px-3 py-1 text-sm shadow-[var(--shadow-xs)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary-default)]"
          />
        </div>
      </div>
      <Dialog.Footer>
        <Button type="button" variant="outline" onclick={() => showCreateRoom = false}>
          Cancelar
        </Button>
        <Button type="submit" class="gap-1.5">
          <Plus class="size-4" />
          Criar Sala
        </Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>

<!-- Invite Guest Dialog -->
<Dialog.Root bind:open={showInvite}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Convidar Visitante</Dialog.Title>
      <Dialog.Description>
        {#if inviteRoom}
          Gere um link de convite para a sala "{inviteRoom.name}".
        {/if}
      </Dialog.Description>
    </Dialog.Header>

    {#if inviteResult}
      <div class="space-y-4 py-4">
        <div class="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--surface-sunken)] p-4">
          <p class="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Link do Convite</p>
          <div class="flex items-center gap-2">
            <code class="flex-1 break-all rounded bg-[var(--surface-default)] px-2 py-1.5 text-xs text-[var(--text-primary)]">{inviteResult.invite_url}</code>
            <Button size="sm" variant="outline" onclick={copyInviteLink} title="Copiar link">
              <Copy class="size-3.5" />
            </Button>
          </div>
        </div>
        <div class="flex items-center gap-4 text-xs text-[var(--text-tertiary)]">
          <span>Convidado: <strong class="text-[var(--text-secondary)]">{inviteResult.guest_name}</strong></span>
          <span>Usos: <strong class="text-[var(--text-secondary)]">{inviteResult.max_uses}</strong></span>
        </div>
      </div>
      <Dialog.Footer>
        <Button onclick={() => { showInvite = false; inviteResult = null; }}>
          Fechar
        </Button>
      </Dialog.Footer>
    {:else}
      <form method="POST" action="?/createInvite" use:enhance>
        <input type="hidden" name="room_id" value={inviteRoom?.id || ''} />
        <div class="space-y-4 py-4">
          <div>
            <label for="guest-name" class="text-sm font-medium text-[var(--text-primary)]">Nome do Visitante</label>
            <input
              id="guest-name"
              name="guest_name"
              type="text"
              required
              placeholder="Nome do convidado"
              class="mt-1.5 flex h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-transparent px-3 py-1 text-sm shadow-[var(--shadow-xs)] transition-colors placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary-default)]"
            />
          </div>
          <div>
            <label for="guest-email" class="text-sm font-medium text-[var(--text-primary)]">Email (opcional)</label>
            <input
              id="guest-email"
              name="guest_email"
              type="email"
              placeholder="email@exemplo.com"
              class="mt-1.5 flex h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-transparent px-3 py-1 text-sm shadow-[var(--shadow-xs)] transition-colors placeholder:text-[var(--text-tertiary)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary-default)]"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="invite-hours" class="text-sm font-medium text-[var(--text-primary)]">Expira em (horas)</label>
              <input
                id="invite-hours"
                name="hours"
                type="number"
                min="1"
                max="168"
                value="24"
                class="mt-1.5 flex h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-transparent px-3 py-1 text-sm shadow-[var(--shadow-xs)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary-default)]"
              />
            </div>
            <div>
              <label for="invite-uses" class="text-sm font-medium text-[var(--text-primary)]">Máx. Usos</label>
              <input
                id="invite-uses"
                name="max_uses"
                type="number"
                min="1"
                max="100"
                value="1"
                class="mt-1.5 flex h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-transparent px-3 py-1 text-sm shadow-[var(--shadow-xs)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary-default)]"
              />
            </div>
          </div>
        </div>
        <Dialog.Footer>
          <Button type="button" variant="outline" onclick={() => showInvite = false}>
            Cancelar
          </Button>
          <Button type="submit" class="gap-1.5">
            <Link class="size-4" />
            Gerar Link
          </Button>
        </Dialog.Footer>
      </form>
    {/if}
  </Dialog.Content>
</Dialog.Root>

<style>
  .fullscreen-container {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    flex-direction: column;
    background: var(--surface-default, hsl(var(--background)));
  }

  .iframe-fullscreen {
    height: calc(100vh - 3rem);
  }

  .loading-bar {
    width: 30%;
    animation: loading 1.5s ease-in-out infinite;
  }

  @keyframes loading {
    0% { transform: translateX(-100%); }
    50% { transform: translateX(250%); }
    100% { transform: translateX(-100%); }
  }
</style>
