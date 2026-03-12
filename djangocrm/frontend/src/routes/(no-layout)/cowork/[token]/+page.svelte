<script>
  import { onDestroy } from 'svelte';
  import { Video } from '@lucide/svelte';
  import { Badge } from '$lib/components/ui/badge/index.js';

  const COWORK_APP_URL = '/cowork-app/';
  const COWORK_SOCKET_URL = `${typeof window !== 'undefined' ? window.location.origin : ''}/cowork-ws`;

  let { data } = $props();

  let room = $derived(data.room);
  let guest = $derived(data.guest);
  let coworkToken = $derived(data.coworkToken);

  let iframeRef = $state(null);
  let iframeReady = $state(false);

  // Listen for postMessage from cowork-app iframe
  function handleMessage(event) {
    const { type, payload } = event.data || {};
    switch (type) {
      case 'cowork-ready':
        iframeReady = true;
        // Send init config to iframe
        if (iframeRef?.contentWindow && coworkToken && room) {
          iframeRef.contentWindow.postMessage({
            type: 'cowork-init',
            payload: {
              socketUrl: COWORK_SOCKET_URL,
              token: coworkToken,
              roomId: room.id,
              displayName: guest?.name || 'Visitante',
              isGuest: true
            }
          }, '*');
        }
        break;
      case 'cowork-error':
        console.error('[Cowork Guest] Error:', payload?.message);
        break;
    }
  }

  // Register/cleanup message listener
  if (typeof window !== 'undefined') {
    window.addEventListener('message', handleMessage);
  }
  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('message', handleMessage);
    }
    if (iframeRef?.contentWindow) {
      iframeRef.contentWindow.postMessage({ type: 'cowork-destroy' }, '*');
    }
  });
</script>

<svelte:head>
  <title>{room?.name || 'Sala Cowork'} — TalkHub</title>
</svelte:head>

<div class="flex h-screen w-screen flex-col bg-background">
  <!-- Minimal header -->
  <header class="flex items-center justify-between border-b px-4 py-2">
    <div class="flex items-center gap-3">
      <Badge variant="default" class="gap-1">
        <Video class="size-3" />
        Cowork
      </Badge>
      <span class="font-medium text-sm">{room?.name}</span>
    </div>
    <div class="flex items-center gap-2 text-sm text-muted-foreground">
      <span>Visitante: <strong>{guest?.name}</strong></span>
    </div>
  </header>

  <!-- Cowork iframe -->
  <main class="relative flex-1">
    <iframe
      bind:this={iframeRef}
      src={COWORK_APP_URL}
      title="Sala Cowork"
      class="h-full w-full border-0"
      allow="camera; microphone; display-capture"
      sandbox="allow-scripts allow-same-origin allow-popups"
    ></iframe>
    {#if !iframeReady}
      <div class="absolute inset-0 flex items-center justify-center bg-muted/80">
        <div class="text-center space-y-2">
          <div class="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
          <p class="text-muted-foreground text-sm">Carregando sala...</p>
        </div>
      </div>
    {/if}
  </main>
</div>
