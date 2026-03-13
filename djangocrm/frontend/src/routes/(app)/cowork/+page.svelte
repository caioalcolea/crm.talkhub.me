<script>
  import { enhance } from '$app/forms';
  import { beforeNavigate } from '$app/navigation';
  import { onDestroy, onMount } from 'svelte';
  import { toast } from 'svelte-sonner';
  import { PageHeader } from '$lib/components/layout';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import {
    Plus, Video, Users, Link, Trash2, Play, Copy, UserPlus,
    Maximize, LogOut, Wifi, WifiOff, PictureInPicture2
  } from '@lucide/svelte';
  import {
    coworkSession, startCoworkSession, endCoworkSession,
    setCoworkMode, registerFullTarget, unregisterFullTarget
  } from '$lib/stores/cowork.svelte.js';

  let { data, form } = $props();

  let rooms = $derived(data.rooms || []);
  let showCreateRoom = $state(false);
  let showInvite = $state(false);
  let inviteRoom = $state(null);
  let inviteResult = $state(null);

  // Target element for the CoworkPiP to overlay in "full" mode
  let iframeTargetRef = $state(null);

  // On mount: if session already active (returning from PiP), switch to full
  onMount(() => {
    if (coworkSession.active && coworkSession.mode === 'pip') {
      setCoworkMode('full');
    }
  });

  // Register/unregister the target element for full-mode overlay
  $effect(() => {
    if (iframeTargetRef && coworkSession.active) {
      registerFullTarget(iframeTargetRef);
    }
  });

  onDestroy(() => {
    unregisterFullTarget();
  });

  // When navigating away while session active, switch to PiP
  beforeNavigate(({ to }) => {
    if (coworkSession.active && coworkSession.mode === 'full') {
      // Only switch to PiP if navigating to a different page
      if (to?.route?.id !== '/(app)/cowork') {
        unregisterFullTarget();
        setCoworkMode('pip');
      }
    }
  });

  // Handle form results
  $effect(() => {
    if (form?.toast) toast.success(form.toast);
    if (form?.error) toast.error(form.error);
    if (form?.coworkToken) {
      const displayName = data.user?.name || data.user?.email || 'User';
      startCoworkSession(form.coworkToken, form.room, displayName);
    }
    if (form?.invite) {
      inviteResult = form.invite;
    }
  });

  // Actions
  function leaveRoom() {
    endCoworkSession();
  }

  function toggleFullscreen() {
    if (coworkSession.mode === 'fullscreen') {
      setCoworkMode('full');
    } else {
      setCoworkMode('fullscreen');
    }
  }

  function minimizeToPip() {
    setCoworkMode('pip');
  }

  function copyInviteLink() {
    if (inviteResult?.invite_url) {
      navigator.clipboard.writeText(inviteResult.invite_url);
      toast.success('Link copiado!');
    }
  }

  function enterRoom(roomId) {
    const formEl = document.getElementById('enter-room-form');
    if (formEl) {
      const input = formEl.querySelector('input[name="room_id"]');
      if (input) input.value = roomId;
      formEl.requestSubmit();
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
  <!-- Page Header — z-20 wrapper keeps it above CoworkPiP overlay (z-15) -->
  <div class="relative z-20">
    <PageHeader
      title="Sala Cowork"
      subtitle={coworkSession.active ? coworkSession.room?.name : 'Escritório virtual'}
    >
      {#snippet actions()}
        {#if !coworkSession.active}
          <Button onclick={() => showCreateRoom = true} class="gap-2">
            <Plus class="size-4" />
            Nova Sala
          </Button>
        {/if}
      {/snippet}
    </PageHeader>
  </div>

  <!-- Active session: toolbar + iframe target -->
  {#if coworkSession.active}
    <!-- Session toolbar — z-20 to stay above CoworkPiP overlay (z-15) -->
    <div class="relative z-20 flex items-center justify-between border-b border-[var(--border-default)] bg-[var(--surface-raised)] px-4 py-2 md:px-6">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium
          {coworkSession.iframeReady
            ? 'bg-[var(--task-completed-bg)] text-[var(--task-completed)] dark:bg-[var(--task-completed)]/15'
            : 'bg-[var(--task-due-today-bg)] text-[var(--task-due-today)] dark:bg-[var(--task-due-today)]/15'
          }">
          {#if coworkSession.iframeReady}
            <Wifi class="size-3" />
            Ao Vivo
          {:else}
            <WifiOff class="size-3 animate-pulse" />
            Conectando...
          {/if}
        </div>
      </div>
      <div class="flex items-center gap-1">
        <Button variant="ghost" size="sm" onclick={() => openInviteDialog(coworkSession.room)} class="gap-1.5 text-[var(--text-secondary)]" title="Convidar visitante">
          <UserPlus class="size-3.5" />
          <span class="hidden lg:inline">Convidar</span>
        </Button>
        <div class="mx-1 h-4 w-px bg-[var(--border-default)]"></div>
        <Button variant="ghost" size="sm" onclick={minimizeToPip} class="gap-1.5 text-[var(--text-secondary)]" title="Mini janela (Picture-in-Picture)">
          <PictureInPicture2 class="size-3.5" />
          <span class="hidden lg:inline">Mini Janela</span>
        </Button>
        <Button variant="ghost" size="sm" onclick={toggleFullscreen} class="gap-1.5 text-[var(--text-secondary)]" title="Tela cheia">
          <Maximize class="size-3.5" />
          <span class="hidden lg:inline">Tela Cheia</span>
        </Button>
        <div class="mx-1 h-4 w-px bg-[var(--border-default)]"></div>
        <Button variant="ghost" size="sm" onclick={leaveRoom} class="gap-1.5 text-[var(--color-negative-default)] hover:text-[var(--color-negative-default)] hover:bg-[var(--color-negative-light)]" title="Sair da sala">
          <LogOut class="size-3.5" />
          <span class="hidden lg:inline">Sair</span>
        </Button>
      </div>
    </div>

    <!-- Iframe target: CoworkPiP will overlay this element -->
    <div
      bind:this={iframeTargetRef}
      class="relative flex-1 overflow-hidden"
      style="height: calc(100vh - 7.75rem);"
    ></div>

  {:else}
    <!-- Room list -->
    <div class="space-y-6 px-6 py-6 md:px-8">
      {#if rooms.length === 0}
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
