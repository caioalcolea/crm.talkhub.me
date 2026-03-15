<script>
  import '../../../../app.css';
  import { onDestroy, onMount } from 'svelte';
  import {
    Maximize, Minimize, Video, Users, Monitor, LogOut, Wifi, WifiOff,
    Mic, MicOff, Camera, CameraOff, MessageSquare,
    ArrowRight, Shield
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
    if (typeof window === 'undefined') return; // SSR guard
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

  let initials = $derived.by(() => {
    const name = guest?.name || 'V';
    return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  });
</script>

<svelte:head>
  <title>{room?.name || 'Sala Cowork'} — TalkHub</title>
  <meta name="theme-color" content="#f5f8fa" />
  {@html '<style>body{margin:0;padding:0;overflow:hidden;background:#f5f8fa}</style>'}
</svelte:head>

<div
  bind:this={containerRef}
  class="relative flex h-dvh w-screen flex-col overflow-hidden"
  style="background:#f5f8fa;"
  onmousemove={handleMouseMove}
>
  {#if showWelcome && !entered}
    <!-- ============ WELCOME SCREEN ============ -->
    <div class="flex flex-1 flex-col items-center justify-center px-4">
      <!-- Brand -->
      <div class="mb-8 flex flex-col items-center gap-4">
        <div class="relative">
          <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#ff7a59] shadow-lg shadow-[#ff7a59]/20">
            <Video class="h-8 w-8 text-white" />
          </div>
          <div class="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border-2 border-[#f5f8fa] bg-emerald-500">
            <Wifi class="h-3 w-3 text-white" />
          </div>
        </div>
        <div class="text-center">
          <h1 class="text-3xl font-bold tracking-tight text-[#33475b] sm:text-4xl">
            TalkHub <span class="text-[#ff7a59]">Cowork</span>
          </h1>
          <p class="mt-1.5 text-sm text-[#7c98b6]">Escritório Virtual Colaborativo</p>
        </div>
      </div>

      <!-- Room Card -->
      <div class="w-full max-w-md">
        <div class="overflow-hidden rounded-lg border border-[#cbd6e2] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.08),0_4px_12px_rgba(0,0,0,0.05)]">
          <!-- Guest banner -->
          <div class="flex items-center gap-3 border-b border-[#cbd6e2] bg-[#fff7ed] px-5 py-3.5">
            <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-[#ff7a59] text-sm font-bold text-white">
              {initials}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-[#33475b]">{guest?.name || 'Visitante'}</p>
              {#if guest?.email}
                <p class="truncate text-xs text-[#7c98b6]">{guest.email}</p>
              {:else}
                <p class="text-xs text-[#7c98b6]">Convidado externo</p>
              {/if}
            </div>
            <div class="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1">
              <span class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span class="text-[11px] font-medium text-emerald-600">Online</span>
            </div>
          </div>

          <!-- Room info -->
          <div class="px-5 py-4">
            <p class="text-[10px] font-semibold uppercase tracking-widest text-[#7c98b6]">Sala</p>
            <p class="mt-1 text-lg font-bold text-[#33475b]">{room?.name || 'Sala Cowork'}</p>

            <div class="mt-3.5 grid grid-cols-3 gap-2.5">
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 text-center">
                <Users class="mx-auto h-3.5 w-3.5 text-[#7c98b6]" />
                <p class="mt-1 text-xs font-semibold text-[#33475b]">{room?.max_participants || 25}</p>
                <p class="text-[10px] text-[#7c98b6]">Max</p>
              </div>
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 text-center">
                <MessageSquare class="mx-auto h-3.5 w-3.5 text-[#7c98b6]" />
                <p class="mt-1 text-xs font-semibold text-[#33475b]">Chat</p>
                <p class="text-[10px] text-[#7c98b6]">Ativo</p>
              </div>
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-2.5 text-center">
                <Shield class="mx-auto h-3.5 w-3.5 text-[#7c98b6]" />
                <p class="mt-1 text-xs font-semibold text-[#33475b]">Seguro</p>
                <p class="text-[10px] text-[#7c98b6]">E2E</p>
              </div>
            </div>
          </div>

          <!-- Enter button -->
          <div class="px-5 pb-5">
            <button
              onclick={enterRoom}
              class="group flex w-full items-center justify-center gap-2.5 rounded-md bg-[#ff7a59] px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-[#ff5c35] active:scale-[0.98]"
            >
              Entrar na Sala
              <ArrowRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>
        </div>

        <!-- Features pills -->
        <div class="mt-3.5 flex flex-wrap items-center justify-center gap-2">
          <div class="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5">
            <Camera class="h-3 w-3 text-[#7c98b6]" />
            <span class="text-[11px] text-[#516f90]">Vídeo</span>
          </div>
          <div class="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5">
            <Mic class="h-3 w-3 text-[#7c98b6]" />
            <span class="text-[11px] text-[#516f90]">Áudio</span>
          </div>
          <div class="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5">
            <Monitor class="h-3 w-3 text-[#7c98b6]" />
            <span class="text-[11px] text-[#516f90]">Tela Cheia</span>
          </div>
          <div class="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5">
            <MessageSquare class="h-3 w-3 text-[#7c98b6]" />
            <span class="text-[11px] text-[#516f90]">Chat</span>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <p class="mt-8 text-[11px] text-[#7c98b6]">
        Powered by <span class="font-medium text-[#516f90]">TalkHub</span>
      </p>
    </div>

  {:else}
    <!-- ============ GAME VIEW ============ -->

    <!-- Top header bar -->
    <header
      class="relative z-20 flex shrink-0 items-center justify-between border-b border-gray-200 px-3 py-2 transition-all duration-300 sm:px-4"
      class:opacity-0={!showControls && isFullscreen}
      class:pointer-events-none={!showControls && isFullscreen}
      class:-translate-y-full={!showControls && isFullscreen}
      style="background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(20px);"
    >
      <!-- Left: Logo + Room name -->
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ff7a59]">
          <Video class="h-4 w-4 text-white" />
        </div>
        <div class="hidden sm:block">
          <p class="text-sm font-semibold leading-none text-[#33475b]">{room?.name || 'Cowork'}</p>
          <p class="mt-0.5 text-[10px] text-[#7c98b6]">TalkHub Cowork</p>
        </div>
        <span class="text-sm font-medium text-[#33475b] sm:hidden">{room?.name || 'Cowork'}</span>
      </div>

      <!-- Center: Connection status -->
      <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        {#if connectionStatus === 'connected'}
          <div class="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1">
            <Wifi class="h-3 w-3 text-emerald-600" />
            <span class="text-xs font-medium text-emerald-600">Conectado</span>
          </div>
        {:else if connectionStatus === 'error'}
          <div class="flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-3 py-1">
            <WifiOff class="h-3 w-3 text-red-500" />
            <span class="text-xs font-medium text-red-500">Erro de Conexão</span>
          </div>
        {:else}
          <div class="flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1">
            <Wifi class="h-3 w-3 animate-pulse text-amber-600" />
            <span class="text-xs font-medium text-amber-600">Conectando...</span>
          </div>
        {/if}
      </div>

      <!-- Right: User + Controls -->
      <div class="flex items-center gap-1.5">
        <!-- User badge (desktop) -->
        <div class="hidden items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-2.5 py-1.5 sm:flex">
          <div class="flex h-5 w-5 items-center justify-center rounded bg-[#ff7a59] text-[9px] font-bold text-white">
            {initials}
          </div>
          <span class="max-w-24 truncate text-xs font-medium text-[#516f90]">{guest?.name || 'Visitante'}</span>
        </div>

        <!-- Mic toggle -->
        <button
          onclick={toggleMute}
          class="flex h-8 w-8 items-center justify-center rounded-md border transition-all
            {isMuted
              ? 'border-red-300 bg-red-50 text-red-500 hover:bg-red-100'
              : 'border-gray-300 bg-white text-gray-500 hover:bg-gray-50 hover:text-[#33475b]'
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
          class="flex h-8 w-8 items-center justify-center rounded-md border transition-all
            {isCameraOff
              ? 'border-red-300 bg-red-50 text-red-500 hover:bg-red-100'
              : 'border-gray-300 bg-white text-gray-500 hover:bg-gray-50 hover:text-[#33475b]'
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
          class="flex h-8 w-8 items-center justify-center rounded-md border border-gray-300 bg-white text-gray-500 transition-all hover:bg-gray-50 hover:text-[#33475b]"
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
          class="flex h-8 items-center gap-1.5 rounded-md border border-red-300 bg-red-50 px-2.5 text-red-500 transition-all hover:bg-red-100"
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
        <div class="absolute inset-0 z-30 flex flex-col items-center justify-center bg-white/95">
          <!-- Animated loader -->
          <div class="relative mb-8">
            <div class="flex h-20 w-20 items-center justify-center rounded-2xl bg-orange-50">
              <Monitor class="h-10 w-10 text-[#ff7a59] animate-pulse" />
            </div>
            <svg class="absolute -inset-3 animate-spin" style="animation-duration: 3s;" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="46" fill="none" stroke="url(#grad)" stroke-width="2" stroke-dasharray="60 230" stroke-linecap="round" />
              <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#ea580c" />
                  <stop offset="100%" stop-color="#f97316" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          <p class="mb-2 text-base font-bold text-[#33475b]">Preparando sua sala...</p>
          <p class="mb-6 text-sm text-[#7c98b6]">Conectando ao escritório virtual</p>

          <!-- Progress -->
          <div class="w-64 overflow-hidden rounded-full bg-gray-200">
            <div
              class="h-1.5 rounded-full bg-gradient-to-r from-orange-500 to-amber-500 transition-all duration-500"
              style="width: {loadProgress}%;"
            ></div>
          </div>
          <p class="mt-3 text-xs text-[#7c98b6]">{Math.round(loadProgress)}%</p>
        </div>
      {/if}
    </main>

    <!-- Bottom control bar (fullscreen auto-hide) -->
    {#if isFullscreen}
      <div
        class="absolute bottom-0 left-0 right-0 z-20 flex items-center justify-center gap-3 border-t border-gray-200 px-4 py-3 transition-all duration-300"
        class:translate-y-full={!showControls}
        class:opacity-0={!showControls}
        style="background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(20px);"
      >
        <button
          onclick={toggleMute}
          class="flex items-center gap-2 rounded-md border px-4 py-2.5 text-sm font-medium transition-all
            {isMuted
              ? 'border-red-300 bg-red-50 text-red-500 hover:bg-red-100'
              : 'border-gray-300 bg-white text-[#516f90] hover:bg-gray-50 hover:text-[#33475b]'
            }"
        >
          {#if isMuted}<MicOff class="h-4 w-4" />{:else}<Mic class="h-4 w-4" />{/if}
          <span class="hidden sm:inline">{isMuted ? 'Mic Off' : 'Mic On'}</span>
        </button>
        <button
          onclick={toggleCamera}
          class="flex items-center gap-2 rounded-md border px-4 py-2.5 text-sm font-medium transition-all
            {isCameraOff
              ? 'border-red-300 bg-red-50 text-red-500 hover:bg-red-100'
              : 'border-gray-300 bg-white text-[#516f90] hover:bg-gray-50 hover:text-[#33475b]'
            }"
        >
          {#if isCameraOff}<CameraOff class="h-4 w-4" />{:else}<Camera class="h-4 w-4" />{/if}
          <span class="hidden sm:inline">{isCameraOff ? 'Cam Off' : 'Cam On'}</span>
        </button>
        <button
          onclick={toggleFullscreen}
          class="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-[#516f90] transition-all hover:bg-gray-50 hover:text-[#33475b]"
        >
          <Minimize class="h-4 w-4" />
          <span class="hidden sm:inline">Sair Fullscreen</span>
        </button>
        <button
          onclick={leaveRoom}
          class="flex items-center gap-2 rounded-md border border-red-300 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-500 transition-all hover:bg-red-100"
        >
          <LogOut class="h-4 w-4" />
          <span class="hidden sm:inline">Sair</span>
        </button>
      </div>
    {/if}
  {/if}
</div>
