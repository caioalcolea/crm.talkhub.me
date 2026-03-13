<script>
  import '../../../../app.css';
  import { onDestroy, onMount } from 'svelte';
  import {
    Maximize, Minimize, Video, Users, Monitor, LogOut, Wifi, WifiOff,
    Volume2, VolumeX, Mic, MicOff, Camera, CameraOff, MessageSquare,
    Sparkles, Shield, Clock, ArrowRight, ExternalLink
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
  let controlTimeout = null;
  let connectionStatus = $state('connecting');
  let loadProgress = $state(0);
  let showWelcome = $state(true);
  let entered = $state(false);
  let isMuted = $state(false);
  let isCameraOff = $state(false);

  // Loading progress simulation
  let progressInterval;
  onMount(() => {
    progressInterval = setInterval(() => {
      if (loadProgress < 90 && !iframeReady) {
        loadProgress += Math.random() * 12;
        if (loadProgress > 90) loadProgress = 90;
      }
    }, 400);
  });

  $effect(() => {
    if (iframeReady) {
      loadProgress = 100;
      connectionStatus = 'connected';
      if (progressInterval) clearInterval(progressInterval);
    }
  });

  // postMessage bridge
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
        break;
    }
  }

  onMount(() => {
    window.addEventListener('message', handleMessage);
    document.addEventListener('fullscreenchange', onFullscreenChange);
  });

  onDestroy(() => {
    window.removeEventListener('message', handleMessage);
    document.removeEventListener('fullscreenchange', onFullscreenChange);
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

  function leaveRoom() {
    if (iframeRef?.contentWindow) {
      iframeRef.contentWindow.postMessage({ type: 'cowork-destroy' }, '*');
    }
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    entered = false;
    showWelcome = true;
    iframeReady = false;
    connectionStatus = 'connecting';
    loadProgress = 0;
  }

  function toggleMute() {
    isMuted = !isMuted;
    iframeRef?.contentWindow?.postMessage({ type: 'cowork-toggle-mute', payload: { muted: isMuted } }, '*');
  }

  function toggleCamera() {
    isCameraOff = !isCameraOff;
    iframeRef?.contentWindow?.postMessage({ type: 'cowork-toggle-camera', payload: { off: isCameraOff } }, '*');
  }

  let initials = $derived(() => {
    const name = guest?.name || 'V';
    return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  });
</script>

<svelte:head>
  <title>{room?.name || 'Sala Cowork'} — TalkHub</title>
  <meta name="theme-color" content="#09090b" />
</svelte:head>

<div
  bind:this={containerRef}
  class="guest-cowork relative flex h-dvh w-screen flex-col overflow-hidden bg-zinc-950"
  onmousemove={handleMouseMove}
>
  <!-- Ambient background -->
  <div class="pointer-events-none absolute inset-0 overflow-hidden">
    <div class="absolute -left-32 -top-32 h-[500px] w-[500px] rounded-full bg-violet-600/8 blur-[120px]"></div>
    <div class="absolute -bottom-32 -right-32 h-[400px] w-[400px] rounded-full bg-blue-600/8 blur-[120px]"></div>
    <div class="absolute left-1/2 top-1/3 h-[300px] w-[300px] -translate-x-1/2 rounded-full bg-emerald-600/5 blur-[100px]"></div>
  </div>

  {#if showWelcome && !entered}
    <!-- ============ WELCOME SCREEN ============ -->
    <div class="relative z-10 flex flex-1 flex-col items-center justify-center px-4">
      <!-- Brand -->
      <div class="mb-10 flex flex-col items-center gap-5">
        <div class="relative">
          <div class="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-violet-500 to-blue-600 shadow-2xl shadow-violet-500/30">
            <Video class="h-10 w-10 text-white" />
          </div>
          <div class="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border-2 border-zinc-950 bg-emerald-500">
            <Wifi class="h-3.5 w-3.5 text-white" />
          </div>
        </div>
        <div class="text-center">
          <h1 class="text-4xl font-bold tracking-tight text-white sm:text-5xl">
            TalkHub <span class="bg-gradient-to-r from-violet-400 to-blue-400 bg-clip-text text-transparent">Cowork</span>
          </h1>
          <p class="mt-2 text-sm text-zinc-500">Escritório Virtual Colaborativo</p>
        </div>
      </div>

      <!-- Room Card -->
      <div class="w-full max-w-md">
        <div class="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900/80 shadow-2xl shadow-black/50 backdrop-blur-xl">
          <!-- Guest banner -->
          <div class="flex items-center gap-3 border-b border-zinc-800 bg-gradient-to-r from-violet-500/10 to-blue-500/10 px-6 py-4">
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-600 text-base font-bold text-white shadow-lg shadow-violet-500/20">
              {initials()}
            </div>
            <div class="flex-1">
              <p class="text-base font-semibold text-white">{guest?.name || 'Visitante'}</p>
              {#if guest?.email}
                <p class="text-xs text-zinc-500">{guest.email}</p>
              {:else}
                <p class="text-xs text-zinc-500">Convidado externo</p>
              {/if}
            </div>
            <div class="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1">
              <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-xs font-medium text-emerald-400">Online</span>
            </div>
          </div>

          <!-- Room info -->
          <div class="px-6 py-5">
            <p class="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">Sala</p>
            <p class="mt-1 text-xl font-bold text-white">{room?.name || 'Sala Cowork'}</p>

            <div class="mt-4 grid grid-cols-3 gap-3">
              <div class="rounded-xl border border-zinc-800 bg-zinc-800/50 p-3 text-center">
                <Users class="mx-auto h-4 w-4 text-zinc-500" />
                <p class="mt-1.5 text-xs font-semibold text-white">{room?.max_participants || 25}</p>
                <p class="text-[10px] text-zinc-600">Max</p>
              </div>
              <div class="rounded-xl border border-zinc-800 bg-zinc-800/50 p-3 text-center">
                <MessageSquare class="mx-auto h-4 w-4 text-zinc-500" />
                <p class="mt-1.5 text-xs font-semibold text-white">Chat</p>
                <p class="text-[10px] text-zinc-600">Ativo</p>
              </div>
              <div class="rounded-xl border border-zinc-800 bg-zinc-800/50 p-3 text-center">
                <Shield class="mx-auto h-4 w-4 text-zinc-500" />
                <p class="mt-1.5 text-xs font-semibold text-white">Seguro</p>
                <p class="text-[10px] text-zinc-600">E2E</p>
              </div>
            </div>
          </div>

          <!-- Enter button -->
          <div class="px-6 pb-6">
            <button
              onclick={enterRoom}
              class="group relative flex w-full items-center justify-center gap-3 overflow-hidden rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-6 py-4 text-base font-bold text-white shadow-xl shadow-violet-600/25 transition-all hover:shadow-2xl hover:shadow-violet-600/40 hover:brightness-110 active:scale-[0.98]"
            >
              <div class="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-700"></div>
              <Sparkles class="h-5 w-5" />
              Entrar na Sala
              <ArrowRight class="h-5 w-5 transition-transform group-hover:translate-x-1" />
            </button>
          </div>
        </div>

        <!-- Features pills -->
        <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
          <div class="flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1.5">
            <Camera class="h-3 w-3 text-zinc-500" />
            <span class="text-[11px] text-zinc-500">Vídeo</span>
          </div>
          <div class="flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1.5">
            <Mic class="h-3 w-3 text-zinc-500" />
            <span class="text-[11px] text-zinc-500">Áudio</span>
          </div>
          <div class="flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1.5">
            <Monitor class="h-3 w-3 text-zinc-500" />
            <span class="text-[11px] text-zinc-500">Tela Cheia</span>
          </div>
          <div class="flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1.5">
            <MessageSquare class="h-3 w-3 text-zinc-500" />
            <span class="text-[11px] text-zinc-500">Chat</span>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <p class="mt-10 text-[11px] text-zinc-700">
        Powered by <span class="font-medium text-zinc-500">TalkHub</span>
      </p>
    </div>

  {:else}
    <!-- ============ GAME VIEW ============ -->

    <!-- Top header bar -->
    <header
      class="relative z-20 flex shrink-0 items-center justify-between border-b border-zinc-800 px-3 py-2 transition-all duration-300 sm:px-4"
      class:opacity-0={!showControls && isFullscreen}
      class:pointer-events-none={!showControls && isFullscreen}
      class:-translate-y-full={!showControls && isFullscreen}
      style="background: rgba(9, 9, 11, 0.85); backdrop-filter: blur(20px);"
    >
      <!-- Left: Logo + Room name -->
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-600">
          <Video class="h-4 w-4 text-white" />
        </div>
        <div class="hidden sm:block">
          <p class="text-sm font-semibold leading-none text-white">{room?.name || 'Cowork'}</p>
          <p class="mt-0.5 text-[10px] text-zinc-500">TalkHub Cowork</p>
        </div>
        <span class="text-sm font-medium text-white sm:hidden">{room?.name || 'Cowork'}</span>
      </div>

      <!-- Center: Connection status -->
      <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        {#if connectionStatus === 'connected'}
          <div class="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1">
            <Wifi class="h-3 w-3 text-emerald-400" />
            <span class="text-xs font-medium text-emerald-400">Conectado</span>
          </div>
        {:else if connectionStatus === 'error'}
          <div class="flex items-center gap-1.5 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1">
            <WifiOff class="h-3 w-3 text-red-400" />
            <span class="text-xs font-medium text-red-400">Erro de Conexão</span>
          </div>
        {:else}
          <div class="flex items-center gap-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1">
            <Wifi class="h-3 w-3 animate-pulse text-amber-400" />
            <span class="text-xs font-medium text-amber-400">Conectando...</span>
          </div>
        {/if}
      </div>

      <!-- Right: User + Controls -->
      <div class="flex items-center gap-1.5">
        <!-- User badge (desktop) -->
        <div class="hidden items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-800/50 px-2.5 py-1.5 sm:flex">
          <div class="flex h-5 w-5 items-center justify-center rounded bg-gradient-to-br from-violet-500 to-blue-600 text-[9px] font-bold text-white">
            {initials()}
          </div>
          <span class="max-w-24 truncate text-xs font-medium text-zinc-400">{guest?.name || 'Visitante'}</span>
        </div>

        <!-- Mic toggle -->
        <button
          onclick={toggleMute}
          class="flex h-8 w-8 items-center justify-center rounded-lg border transition-all
            {isMuted
              ? 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20'
              : 'border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700 hover:text-white'
            }"
          title={isMuted ? 'Ativar microfone' : 'Desativar microfone'}
        >
          {#if isMuted}
            <MicOff class="h-3.5 w-3.5" />
          {:else}
            <Mic class="h-3.5 w-3.5" />
          {/if}
        </button>

        <!-- Camera toggle -->
        <button
          onclick={toggleCamera}
          class="flex h-8 w-8 items-center justify-center rounded-lg border transition-all
            {isCameraOff
              ? 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20'
              : 'border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700 hover:text-white'
            }"
          title={isCameraOff ? 'Ativar câmera' : 'Desativar câmera'}
        >
          {#if isCameraOff}
            <CameraOff class="h-3.5 w-3.5" />
          {:else}
            <Camera class="h-3.5 w-3.5" />
          {/if}
        </button>

        <!-- Fullscreen -->
        <button
          onclick={toggleFullscreen}
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800/50 text-zinc-400 transition-all hover:bg-zinc-700 hover:text-white"
          title={isFullscreen ? 'Sair do fullscreen' : 'Tela cheia'}
        >
          {#if isFullscreen}
            <Minimize class="h-3.5 w-3.5" />
          {:else}
            <Maximize class="h-3.5 w-3.5" />
          {/if}
        </button>

        <!-- Leave -->
        <button
          onclick={leaveRoom}
          class="flex h-8 items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 text-red-400 transition-all hover:bg-red-500/20"
          title="Sair da sala"
        >
          <LogOut class="h-3.5 w-3.5" />
          <span class="hidden text-xs font-medium sm:inline">Sair</span>
        </button>
      </div>
    </header>

    <!-- Iframe container — fills remaining viewport -->
    <main class="relative z-10 min-h-0 flex-1">
      <iframe
        bind:this={iframeRef}
        src={COWORK_APP_URL}
        title="Sala Cowork"
        class="absolute inset-0 h-full w-full border-0"
        allow="camera; microphone; display-capture"
        sandbox="allow-scripts allow-same-origin allow-popups"
      ></iframe>

      <!-- Loading overlay -->
      {#if !iframeReady}
        <div class="absolute inset-0 z-30 flex flex-col items-center justify-center bg-zinc-950/95">
          <!-- Animated loader -->
          <div class="relative mb-8">
            <div class="flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-violet-500/20 to-blue-500/20">
              <Monitor class="h-12 w-12 text-violet-400 animate-pulse" />
            </div>
            <svg class="absolute -inset-3 animate-spin" style="animation-duration: 3s;" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="46" fill="none" stroke="url(#grad)" stroke-width="2" stroke-dasharray="60 230" stroke-linecap="round" />
              <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#8b5cf6" />
                  <stop offset="100%" stop-color="#3b82f6" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          <p class="mb-2 text-lg font-bold text-white">Preparando sua sala...</p>
          <p class="mb-6 text-sm text-zinc-500">Conectando ao escritório virtual</p>

          <!-- Progress -->
          <div class="w-64 overflow-hidden rounded-full bg-zinc-800">
            <div
              class="h-1.5 rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all duration-500"
              style="width: {loadProgress}%;"
            ></div>
          </div>
          <p class="mt-3 text-xs text-zinc-600">{Math.round(loadProgress)}%</p>
        </div>
      {/if}
    </main>

    <!-- Bottom control bar (fullscreen auto-hide) -->
    {#if isFullscreen}
      <div
        class="absolute bottom-0 left-0 right-0 z-20 flex items-center justify-center gap-3 border-t border-zinc-800 px-4 py-3 transition-all duration-300"
        class:translate-y-full={!showControls}
        class:opacity-0={!showControls}
        style="background: rgba(9, 9, 11, 0.9); backdrop-filter: blur(20px);"
      >
        <button
          onclick={toggleMute}
          class="flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all
            {isMuted
              ? 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20'
              : 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white'
            }"
        >
          {#if isMuted}<MicOff class="h-4 w-4" />{:else}<Mic class="h-4 w-4" />{/if}
          <span class="hidden sm:inline">{isMuted ? 'Mic Off' : 'Mic On'}</span>
        </button>
        <button
          onclick={toggleCamera}
          class="flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all
            {isCameraOff
              ? 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20'
              : 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white'
            }"
        >
          {#if isCameraOff}<CameraOff class="h-4 w-4" />{:else}<Camera class="h-4 w-4" />{/if}
          <span class="hidden sm:inline">{isCameraOff ? 'Cam Off' : 'Cam On'}</span>
        </button>
        <button
          onclick={toggleFullscreen}
          class="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 transition-all hover:bg-zinc-700 hover:text-white"
        >
          <Minimize class="h-4 w-4" />
          <span class="hidden sm:inline">Sair Fullscreen</span>
        </button>
        <button
          onclick={leaveRoom}
          class="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm font-medium text-red-400 transition-all hover:bg-red-500/20"
        >
          <LogOut class="h-4 w-4" />
          <span class="hidden sm:inline">Sair</span>
        </button>
      </div>
    {/if}
  {/if}
</div>

<style>
  .guest-cowork :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: #09090b;
  }
</style>
