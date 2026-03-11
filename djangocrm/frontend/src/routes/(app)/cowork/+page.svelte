<script>
  import { enhance } from '$app/forms';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import {
    Plus, Video, Users, Link, Trash2, Play, Copy, UserPlus
  } from '@lucide/svelte';

  let { data, form } = $props();

  let rooms = $derived(data.rooms || []);
  let selectedRoom = $state(null);
  let coworkToken = $state(null);
  let showCreateRoom = $state(false);
  let showInvite = $state(false);
  let inviteRoom = $state(null);
  let inviteResult = $state(null);

  $effect(() => {
    if (form?.toast) toast.success(form.toast);
    if (form?.error) toast.error(form.error);
    if (form?.coworkToken) {
      coworkToken = form.coworkToken;
      selectedRoom = form.room;
    }
    if (form?.invite) {
      inviteResult = form.invite;
    }
  });

  function copyInviteLink() {
    if (inviteResult?.invite_url) {
      navigator.clipboard.writeText(inviteResult.invite_url);
      toast.success('Link copiado!');
    }
  }

  function enterRoom(roomId) {
    // Submit form to get cowork token
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
  <title>Sala Cowork — TalkHub CRM</title>
</svelte:head>

<!-- Hidden form for entering rooms -->
<form id="enter-room-form" method="POST" action="?/getToken" use:enhance class="hidden">
  <input type="hidden" name="room_id" value="" />
</form>

<div class="mx-auto max-w-6xl space-y-6 p-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Sala Cowork</h1>
      <p class="text-muted-foreground text-sm">Salas virtuais de coworking para sua equipe.</p>
    </div>
    <Button onclick={() => showCreateRoom = true} class="gap-2">
      <Plus class="size-4" />
      Nova Sala
    </Button>
  </div>

  <!-- Active cowork session -->
  {#if coworkToken && selectedRoom}
    <div class="rounded-lg border bg-card overflow-hidden">
      <div class="flex items-center justify-between border-b px-4 py-3">
        <div class="flex items-center gap-3">
          <Badge variant="default" class="gap-1">
            <Video class="size-3" />
            Ao Vivo
          </Badge>
          <span class="font-medium">{selectedRoom.name}</span>
        </div>
        <Button variant="outline" size="sm" onclick={() => { coworkToken = null; selectedRoom = null; }}>
          Sair da Sala
        </Button>
      </div>
      <div class="bg-muted/50 flex items-center justify-center p-8" style="min-height: 500px;">
        <div class="text-center space-y-4">
          <Video class="mx-auto size-16 text-muted-foreground" strokeWidth={1} />
          <p class="text-muted-foreground text-lg font-medium">Sala Cowork Ativa</p>
          <p class="text-muted-foreground text-sm max-w-md">
            O iframe do cowork-app será renderizado aqui quando o serviço Socket.io estiver configurado.
            Token JWT gerado com sucesso para a sala "{selectedRoom.name}".
          </p>
          <Badge variant="outline" class="font-mono text-xs">
            Token: {coworkToken.substring(0, 20)}...
          </Badge>
        </div>
      </div>
    </div>
  {/if}

  <!-- Room list -->
  {#if rooms.length === 0 && !coworkToken}
    <div class="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
      <Video class="text-muted-foreground mb-4 size-12" strokeWidth={1} />
      <p class="text-muted-foreground text-lg font-medium">Nenhuma sala criada</p>
      <p class="text-muted-foreground mt-1 text-sm">Crie sua primeira sala virtual para começar.</p>
      <Button onclick={() => showCreateRoom = true} class="mt-4 gap-2" variant="outline">
        <Plus class="size-4" />
        Criar Sala
      </Button>
    </div>
  {:else if !coworkToken}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each rooms as room (room.id)}
        <div class="rounded-lg border bg-card p-5 space-y-4 hover:shadow-sm transition-shadow">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-semibold">{room.name}</h3>
              <p class="text-muted-foreground text-xs mt-1">Mapa: {room.map_id}</p>
            </div>
            <Badge variant="outline" class="gap-1 text-xs">
              <Users class="size-3" />
              {room.participant_count || 0} / {room.max_participants}
            </Badge>
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
            >
              <UserPlus class="size-3.5" />
            </Button>
            <form method="POST" action="?/deleteRoom" use:enhance>
              <input type="hidden" name="id" value={room.id} />
              <Button
                type="submit"
                size="sm"
                variant="ghost"
                class="text-destructive hover:text-destructive"
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
          <label for="room-name" class="text-sm font-medium">Nome da Sala</label>
          <input
            id="room-name"
            name="name"
            type="text"
            required
            placeholder="Ex: Escritório Principal"
            class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
        <div>
          <label for="room-map" class="text-sm font-medium">Mapa</label>
          <select
            id="room-map"
            name="map_id"
            class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          >
            <option value="office_default">Escritório Padrão</option>
            <option value="open_space">Open Space</option>
            <option value="meeting_room">Sala de Reunião</option>
          </select>
        </div>
        <div>
          <label for="room-max" class="text-sm font-medium">Máx. Participantes</label>
          <input
            id="room-max"
            name="max_participants"
            type="number"
            min="2"
            max="50"
            value="25"
            class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
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
      <!-- Show invite link -->
      <div class="space-y-4 py-4">
        <div class="rounded-md bg-muted p-3">
          <p class="text-sm font-medium mb-1">Link do Convite:</p>
          <div class="flex items-center gap-2">
            <code class="text-xs break-all flex-1">{inviteResult.invite_url}</code>
            <Button size="sm" variant="outline" onclick={copyInviteLink}>
              <Copy class="size-3.5" />
            </Button>
          </div>
        </div>
        <p class="text-muted-foreground text-xs">
          Convidado: {inviteResult.guest_name} · Usos: {inviteResult.max_uses}
        </p>
      </div>
      <Dialog.Footer>
        <Button onclick={() => { showInvite = false; inviteResult = null; }}>
          Fechar
        </Button>
      </Dialog.Footer>
    {:else}
      <!-- Invite form -->
      <form method="POST" action="?/createInvite" use:enhance>
        <input type="hidden" name="room_id" value={inviteRoom?.id || ''} />
        <div class="space-y-4 py-4">
          <div>
            <label for="guest-name" class="text-sm font-medium">Nome do Visitante</label>
            <input
              id="guest-name"
              name="guest_name"
              type="text"
              required
              placeholder="Nome do convidado"
              class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <div>
            <label for="guest-email" class="text-sm font-medium">Email (opcional)</label>
            <input
              id="guest-email"
              name="guest_email"
              type="email"
              placeholder="email@exemplo.com"
              class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="invite-hours" class="text-sm font-medium">Expira em (horas)</label>
              <input
                id="invite-hours"
                name="hours"
                type="number"
                min="1"
                max="168"
                value="24"
                class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              />
            </div>
            <div>
              <label for="invite-uses" class="text-sm font-medium">Máx. Usos</label>
              <input
                id="invite-uses"
                name="max_uses"
                type="number"
                min="1"
                max="100"
                value="1"
                class="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
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
