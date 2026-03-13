<script>
  import { onDestroy, onMount } from 'svelte';
  import {
    Maximize, Minimize, Video, Users, Mic, MicOff,
    Camera, CameraOff, Monitor, LogOut, Wifi, WifiOff,
    Volume2
  } from '@lucide/svelte';

  const COWORK_APP_URL = '/cowork-app/';
  const COWORK_SOCKET_URL = `${typeof window !== 'undefined' ? window.location.origin : ''}/cowork-ws`;

  let { data } = $props();

  let room = $derived(data.room);
  let guest = $derived(data.guest);
  let coworkToken = $derived(data.coworkToken);

  let iframeRef = $state(null);
  let containerRef = $state(null);
  let iframeReady = $state(false);
  let isFullscreen = $state(false);
  let showControls = $state(true);
  let controlTimeout = $state(null);
  let connectionStatus = $state('connecting'); // connecting | connected | error
  let loadProgress = $state(0);
  let showWelcome = $state(true);
  let entered = $state(false);

  // Simulate loading progress
  let progressInterval;
  onMount(() => {
    progressInterval = setInterval(() => {
      if (loadProgress < 90 && !iframeReady) {
        loadProgress += Math.random() * 15;
        if (loadProgress > 90) loadProgress = 90;
      }
    }, 300);
  });

  $effect(() => {
    if (iframeReady) {
      loadProgress = 100;
      connectionStatus = 'connected';
      if (progressInterval) clearInterval(progressInterval);
    }
  });

  // Listen for postMessage from cowork-app iframe
  function handleMessage(event) {
    const { type, payload } = event.data || {};
    switch (type) {
      case 'cowork-ready':
        iframeReady = true;
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
        connectionStatus = 'error';
        console.error('[Cowork Guest] Error:', payload?.message);
        break;
    }
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('message', handleMessage);
  }

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('message', handleMessage);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    }
    if (iframeRef?.contentWindow) {
      iframeRef.contentWindow.postMessage({ type: 'cowork-destroy' }, '*');
    }
    if (progressInterval) clearInterval(progressInterval);
    if (controlTimeout) clearTimeout(controlTimeout);
  });

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

  onMount(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
  });

  // Auto-hide controls on mouse idle (fullscreen)
  function handleMouseMove() {
    showControls = true;
    if (controlTimeout) clearTimeout(controlTimeout);
    if (isFullscreen) {
      controlTimeout = setTimeout(() => { showControls = false; }, 3000);
    }
  }

  function enterRoom() {
    showWelcome = false;
    entered = true;
  }

  // Initials for avatar
  let initials = $derived(() => {
    const name = guest?.name || 'V';
    return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  });
</script>

<svelte:head>
  <title>{room?.name || 'Sala Cowork'} — TalkHub</title>
  <meta name="theme-color" content="#0f0f23" />
</svelte:head>

<!-- Full viewport container -->
<div
  bind:this={containerRef}
  class="relative flex h-[100dvh] w-screen flex-col overflow-hidden bg-[#0a0a1a]"
  onmousemove={handleMouseMove}
>
  <!-- Animated background gradient -->
  <div class="pointer-events-none absolute inset-0 overflow-hidden">
    <div class="absolute -left-1/4 -top-1/4 h-[600px] w-[600px] rounded-full bg-violet-600/10 blur-[120px] animate-pulse"></div>
    <div class="absolute -bottom-1/4 -right-1/4 h-[500px] w-[500px] rounded-full bg-blue-600/10 blur-[120px] animate-pulse" style="animation-delay: 1s;"></div>
    <div class="absolute left-1/2 top-1/2 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-600/5 blur-[100px] animate-pulse" style="animation-delay: 2s;"></div>
  </div>

  {#if showWelcome && !entered}
    <!-- Welcome Screen -->
    <div class="relative z-10 flex flex-1 flex-col items-center justify-center px-4">
      <!-- Logo / Brand -->
      <div class="mb-8 flex flex-col items-center gap-4">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-600 shadow-lg shadow-violet-500/25">
          <Video class="h-8 w-8 text-white" />
        </div>
        <div class="text-center">
          <h1 class="bg-gradient-to-r from-white to-white/60 bg-clip-text text-3xl font-bold tracking-tight text-transparent sm:text-4xl">
            TalkHub Cowork
          </h1>
          <p class="mt-1 text-sm text-white/40">Escritório Virtual</p>
        </div>
      </div>

      <!-- Room Card -->
      <div class="w-full max-w-sm overflow-hidden rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl">
        <!-- Room header -->
        <div class="border-b border-white/10 px-6 py-5">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-sm font-bold text-white shadow-lg shadow-emerald-500/20">
              {initials()}
            </div>
            <div>
              <p class="font-semibold text-white">{guest?.name || 'Visitante'}</p>
              <p class="text-xs text-white/40">Convidado</p>
            </div>
          </div>
        </div>

        <!-- Room info -->
        <div class="space-y-4 px-6 py-5">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium uppercase tracking-widest text-white/30">Sala</p>
              <p class="mt-1 text-lg font-semibold text-white">{room?.name || 'Sala Cowork'}</p>
            </div>
            <div class="flex h-8 items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3">
              <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-xs font-medium text-emerald-400">Online</span>
            </div>
          </div>

          {#if room?.max_participants}
            <div class="flex items-center gap-2 text-white/40">
              <Users class="h-3.5 w-3.5" />
              <span class="text-xs">Até {room.max_participants} participantes</span>
            </div>
          {/if}
        </div>

        <!-- Enter button -->
        <div class="px-6 pb-6">
          <button
            onclick={enterRoom}
            class="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-6 py-3.5 font-semibold text-white shadow-lg shadow-violet-500/25 transition-all hover:shadow-xl hover:shadow-violet-500/30 hover:brightness-110 active:scale-[0.98]"
          >
            <div class="absolute inset-0 bg-gradient-to-r from-violet-400 to-blue-400 opacity-0 transition-opacity group-hover:opacity-20"></div>
            <Video class="h-5 w-5" />
            Entrar na Sala
          </button>
        </div>
      </div>

      <!-- Footer brand -->
      <p class="mt-8 text-xs text-white/20">
        Powered by <span class="font-medium text-white/30">TalkHub</span>
      </p>
    </div>

  {:else}
    <!-- Game View -->

    <!-- Top bar (glassmorphism) -->
    <header
      class="relative z-20 flex items-center justify-between border-b border-white/10 px-3 py-2 transition-all duration-300 sm:px-4"
      class:opacity-0={!showControls && isFullscreen}
      class:pointer-events-none={!showControls && isFullscreen}
      style="background: rgba(10, 10, 26, 0.8); backdrop-filter: blur(20px);"
    >
      <!-- Left: Logo + Room name -->
      <div class="flex items-center gap-2 sm:gap-3">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-600 shadow shadow-violet-500/20">
          <Video class="h-4 w-4 text-white" />
        </div>
        <div class="hidden sm:block">
          <p class="text-sm font-semibold text-white leading-none">{room?.name || 'Cowork'}</p>
          <p class="text-[10px] text-white/40 mt-0.5">TalkHub Cowork</p>
        </div>
        <span class="text-sm font-medium text-white sm:hidden">{room?.name || 'Cowork'}</span>
      </div>

      <!-- Center: Status -->
      <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        {#if connectionStatus === 'connected'}
          <div class="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1">
            <Wifi class="h-3 w-3 text-emerald-400" />
            <span class="text-xs font-medium text-emerald-400">Conectado</span>
          </div>
        {:else if connectionStatus === 'error'}
          <div class="flex items-center gap-1.5 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1">
            <WifiOff class="h-3 w-3 text-red-400" />
            <span class="text-xs font-medium text-red-400">Erro</span>
          </div>
        {:else}
          <div class="flex items-center gap-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1">
            <Wifi class="h-3 w-3 text-amber-400 animate-pulse" />
            <span class="text-xs font-medium text-amber-400">Conectando...</span>
          </div>
        {/if}
      </div>

      <!-- Right: User + Controls -->
      <div class="flex items-center gap-2">
        <div class="hidden items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 sm:flex">
          <div class="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-emerald-400 to-emerald-600 text-[10px] font-bold text-white">
            {initials()}
          </div>
          <span class="text-xs font-medium text-white/70">{guest?.name || 'Visitante'}</span>
        </div>

        <!-- Fullscreen toggle -->
        <button
          onclick={toggleFullscreen}
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white/60 transition-all hover:bg-white/10 hover:text-white"
          title={isFullscreen ? 'Sair do fullscreen' : 'Fullscreen'}
        >
          {#if isFullscreen}
            <Minimize class="h-4 w-4" />
          {:else}
            <Maximize class="h-4 w-4" />
          {/if}
        </button>
      </div>
    </header>

    <!-- Iframe container -->
    <main class="relative z-10 flex-1">
      <iframe
        bind:this={iframeRef}
        src={COWORK_APP_URL}
        title="Sala Cowork"
        class="h-full w-full border-0"
        allow="camera; microphone; display-capture"
        sandbox="allow-scripts allow-same-origin allow-popups"
      ></iframe>

      <!-- Loading overlay -->
      {#if !iframeReady}
        <div class="absolute inset-0 z-30 flex flex-col items-center justify-center" style="background: rgba(10, 10, 26, 0.95);">
          <!-- Animated loader -->
          <div class="relative mb-8">
            <div class="h-20 w-20 rounded-2xl bg-gradient-to-br from-violet-500/20 to-blue-500/20 flex items-center justify-center">
              <Video class="h-10 w-10 text-violet-400 animate-pulse" />
            </div>
            <!-- Spinning ring -->
            <svg class="absolute -inset-2 animate-spin" style="animation-duration: 3s;" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="46" fill="none" stroke="url(#gradient)" stroke-width="2" stroke-dasharray="60 230" stroke-linecap="round" />
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#8b5cf6" />
                  <stop offset="100%" stop-color="#3b82f6" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          <p class="mb-2 text-lg font-semibold text-white">Preparando sua sala...</p>
          <p class="mb-6 text-sm text-white/40">Conectando ao escritório virtual</p>

          <!-- Progress bar -->
          <div class="w-64 overflow-hidden rounded-full bg-white/10">
            <div
              class="h-1 rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all duration-500"
              style="width: {loadProgress}%;"
            ></div>
          </div>
          <p class="mt-2 text-xs text-white/30">{Math.round(loadProgress)}%</p>
        </div>
      {/if}
    </main>

    <!-- Bottom control bar (fullscreen only, auto-hides) -->
    {#if isFullscreen}
      <div
        class="absolute bottom-0 left-0 right-0 z-20 flex items-center justify-center gap-2 border-t border-white/10 px-4 py-3 transition-all duration-300"
        class:translate-y-full={!showControls}
        class:opacity-0={!showControls}
        style="background: rgba(10, 10, 26, 0.85); backdrop-filter: blur(20px);"
      >
        <button
          onclick={toggleFullscreen}
          class="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/70 transition-all hover:bg-white/10 hover:text-white"
        >
          <Minimize class="h-4 w-4" />
          <span class="hidden sm:inline">Sair do Fullscreen</span>
          <span class="sm:hidden">ESC</span>
        </button>
      </div>
    {/if}
  {/if}
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: #0a0a1a;
  }
</style>
