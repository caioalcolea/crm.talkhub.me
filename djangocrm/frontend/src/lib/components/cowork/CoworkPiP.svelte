<script>
  /**
   * CoworkPiP — Global cowork iframe with Full / PiP / Fullscreen modes.
   *
   * Renders a SINGLE iframe that persists across mode switches and route
   * navigations. The container style changes based on mode — the iframe
   * DOM node is never destroyed/recreated, so the Phaser game stays alive.
   */
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import { Button } from '$lib/components/ui/button/index.js';
  import {
    Minimize, X, Wifi, WifiOff, Monitor, Maximize,
    LogOut, GripHorizontal, Maximize2, Minimize2, PictureInPicture2
  } from '@lucide/svelte';
  import {
    coworkSession, endCoworkSession, setCoworkMode, setIframeReady,
    registerFullTarget
  } from '$lib/stores/cowork.svelte.js';

  // --- PiP drag state ---
  let pipEl = $state(null);
  let pipX = $state(null);
  let pipY = $state(null);
  let dragging = $state(false);
  let dragOffsetX = 0;
  let dragOffsetY = 0;

  // --- PiP size presets ---
  const PIP_SIZES = {
    sm: { w: 320, h: 208, label: 'P' },
    md: { w: 480, h: 312, label: 'M' },
    lg: { w: 640, h: 416, label: 'G' }
  };
  let pipSize = $state('sm');

  // --- Fullscreen auto-hide ---
  let showFsControls = $state(true);
  let fsControlTimeout = null;

  // --- Full-mode overlay bounds ---
  let fullBounds = $state(null);

  // --- Refs ---
  let iframeRef = $state(null);
  let fullscreenContainerRef = $state(null);
  let modeBeforeFullscreen = $state('full');

  // ====================== postMessage ======================

  function handleMessage(event) {
    const { type, payload } = event.data || {};
    switch (type) {
      case 'cowork-ready':
        setIframeReady(true);
        sendInit();
        break;
      case 'cowork-error':
        toast.error(payload?.message || 'Erro no cowork');
        break;
    }
  }

  function sendInit() {
    if (!iframeRef?.contentWindow || !coworkSession.token || !coworkSession.room) return;
    iframeRef.contentWindow.postMessage({
      type: 'cowork-init',
      payload: {
        socketUrl: coworkSession.socketUrl,
        token: coworkSession.token,
        roomId: coworkSession.room.id,
        displayName: coworkSession.displayName || 'User',
        isGuest: coworkSession.isGuest
      }
    }, '*');
  }

  // ====================== Full-mode ResizeObserver ======================

  let resizeObserver = null;

  $effect(() => {
    let target = coworkSession.fullTarget;
    const currentMode = coworkSession.mode;

    // Backup: if fullTarget wasn't registered by the page effect, query DOM directly
    if (currentMode === 'full' && !target) {
      target = document.querySelector('[data-cowork-target]');
      if (target) registerFullTarget(target);
    }

    if (currentMode === 'full' && target) {
      const update = () => {
        const rect = target.getBoundingClientRect();
        fullBounds = { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
      };
      update();
      resizeObserver = new ResizeObserver(update);
      resizeObserver.observe(target);
      window.addEventListener('resize', update);
      return () => {
        resizeObserver?.disconnect();
        resizeObserver = null;
        window.removeEventListener('resize', update);
      };
    } else {
      fullBounds = null;
    }
  });

  // ====================== Lifecycle ======================

  onMount(() => {
    window.addEventListener('message', handleMessage);
    document.addEventListener('fullscreenchange', onBrowserFullscreenChange);
  });

  onDestroy(() => {
    window.removeEventListener('message', handleMessage);
    document.removeEventListener('fullscreenchange', onBrowserFullscreenChange);
    if (fsControlTimeout) clearTimeout(fsControlTimeout);
    resizeObserver?.disconnect();
  });

  // ====================== Actions ======================

  function handleLeave() {
    if (iframeRef?.contentWindow) {
      iframeRef.contentWindow.postMessage({ type: 'cowork-destroy' }, '*');
    }
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    endCoworkSession();
  }

  function handleExpand() {
    setCoworkMode('full');
    goto('/cowork');
  }

  function toggleFullscreen() {
    if (coworkSession.mode === 'fullscreen') {
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
      setCoworkMode(modeBeforeFullscreen);
    } else {
      modeBeforeFullscreen = coworkSession.mode;
      setCoworkMode('fullscreen');
      fullscreenContainerRef?.requestFullscreen?.().catch(() => {});
    }
  }

  function switchToPip() {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    setCoworkMode('pip');
  }

  function onBrowserFullscreenChange() {
    if (!document.fullscreenElement && coworkSession.mode === 'fullscreen') {
      setCoworkMode(modeBeforeFullscreen);
    }
  }

  function cyclePipSize() {
    const order = ['sm', 'md', 'lg'];
    const idx = order.indexOf(pipSize);
    pipSize = order[(idx + 1) % order.length];
  }

  function handleFsMouseMove() {
    showFsControls = true;
    if (fsControlTimeout) clearTimeout(fsControlTimeout);
    if (coworkSession.mode === 'fullscreen') {
      fsControlTimeout = setTimeout(() => { showFsControls = false; }, 3000);
    }
  }

  // ====================== PiP Drag ======================

  function onDragStart(e) {
    if (!pipEl) return;
    dragging = true;
    const rect = pipEl.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    window.addEventListener('mousemove', onDragMove);
    window.addEventListener('mouseup', onDragEnd);
  }

  function onDragMove(e) {
    if (!dragging) return;
    e.preventDefault();
    const size = PIP_SIZES[pipSize];
    const maxX = window.innerWidth - size.w;
    const maxY = window.innerHeight - size.h;
    pipX = Math.max(0, Math.min(e.clientX - dragOffsetX, maxX));
    pipY = Math.max(0, Math.min(e.clientY - dragOffsetY, maxY));
  }

  function onDragEnd() {
    dragging = false;
    window.removeEventListener('mousemove', onDragMove);
    window.removeEventListener('mouseup', onDragEnd);
  }

  // ====================== Computed container style ======================

  let containerStyle = $derived.by(() => {
    const m = coworkSession.mode;

    if (m === 'fullscreen') {
      return 'position:fixed;inset:0;z-index:50;';
    }

    if (m === 'pip') {
      const size = PIP_SIZES[pipSize];
      if (pipX !== null && pipY !== null) {
        return `position:fixed;top:${pipY}px;left:${pipX}px;width:${size.w}px;height:${size.h}px;z-index:40;`;
      }
      return `position:fixed;bottom:1.5rem;right:1.5rem;width:${size.w}px;height:${size.h}px;z-index:40;`;
    }

    if (m === 'full') {
      if (fullBounds) {
        // Exact pixel positioning from ResizeObserver
        return `position:fixed;top:${fullBounds.top}px;left:${fullBounds.left}px;width:${fullBounds.width}px;height:${fullBounds.height}px;z-index:15;`;
      }
      // CSS-based approximate positioning — visible immediately, no JS measurement needed.
      // Uses --sidebar-width from :root (260px) and known header+toolbar height (7.75rem).
      // ResizeObserver will refine to exact pixels once the target element is available.
      return 'position:fixed;top:7.75rem;left:var(--sidebar-width,260px);right:0;bottom:0;z-index:15;';
    }

    // hidden
    return 'position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;overflow:hidden;';
  });

  let isFullscreen = $derived(coworkSession.mode === 'fullscreen');
  let isPip = $derived(coworkSession.mode === 'pip');
  let isFull = $derived(coworkSession.mode === 'full');
</script>

{#if coworkSession.active}
  <div
    bind:this={fullscreenContainerRef}
    style={containerStyle}
    class="flex flex-col overflow-hidden bg-[var(--surface-default)]"
    class:rounded-[var(--radius-lg)]={isPip}
    class:border={isPip}
    class:border-[var(--border-default)]={isPip}
    class:shadow-lg={isPip && !dragging}
    class:shadow-2xl={isPip && dragging}
    class:transition-[width,height]={isPip}
    class:duration-200={isPip}
    onmousemove={isFullscreen ? handleFsMouseMove : undefined}
  >
    <!-- ===== TOOLBAR: Fullscreen ===== -->
    {#if isFullscreen}
      <div
        class="flex shrink-0 items-center justify-between border-b border-[var(--border-default)] bg-[var(--surface-raised)] px-4 py-2 transition-all duration-300"
        class:opacity-0={!showFsControls}
        class:pointer-events-none={!showFsControls}
        class:-translate-y-full={!showFsControls}
      >
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
          <span class="text-sm font-semibold text-[var(--text-primary)]">{coworkSession.room?.name}</span>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" onclick={switchToPip} class="gap-1.5">
            <PictureInPicture2 class="size-3.5" />
            <span class="hidden sm:inline">Mini Janela</span>
          </Button>
          <Button variant="outline" size="sm" onclick={toggleFullscreen} class="gap-1.5">
            <Minimize class="size-3.5" />
            <span class="hidden sm:inline">Sair Fullscreen</span>
          </Button>
          <Button variant="outline" size="sm" onclick={handleLeave} class="gap-1.5">
            <LogOut class="size-3.5" />
            <span class="hidden sm:inline">Sair</span>
          </Button>
        </div>
      </div>
    {/if}

    <!-- ===== TOOLBAR: PiP ===== -->
    {#if isPip}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        bind:this={pipEl}
        class="flex shrink-0 cursor-grab items-center justify-between gap-1 border-b border-[var(--border-default)] bg-[var(--surface-raised)] px-2.5 py-1.5 select-none active:cursor-grabbing"
        onmousedown={onDragStart}
      >
        <div class="flex items-center gap-1.5 overflow-hidden">
          <GripHorizontal class="size-3 shrink-0 text-[var(--text-tertiary)]" />
          <span class="h-2 w-2 shrink-0 rounded-full {coworkSession.iframeReady ? 'bg-[var(--task-completed)]' : 'bg-[var(--task-due-today)] animate-pulse'}"></span>
          <span class="truncate text-xs font-medium text-[var(--text-primary)]">{coworkSession.room?.name}</span>
        </div>
        <div class="flex shrink-0 items-center gap-0.5">
          <button
            onclick={cyclePipSize}
            class="flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text-secondary)]"
            title="Redimensionar ({PIP_SIZES[pipSize].label})"
          >
            {PIP_SIZES[pipSize].label}
          </button>
          <button
            onclick={handleExpand}
            class="flex h-5 w-5 items-center justify-center rounded text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text-secondary)]"
            title="Expandir"
          >
            <Maximize2 class="size-3" />
          </button>
          <button
            onclick={toggleFullscreen}
            class="flex h-5 w-5 items-center justify-center rounded text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text-secondary)]"
            title="Tela cheia"
          >
            <Maximize class="size-3" />
          </button>
          <button
            onclick={handleLeave}
            class="flex h-5 w-5 items-center justify-center rounded text-[var(--text-tertiary)] transition-colors hover:bg-[var(--color-negative-light)] hover:text-[var(--color-negative-default)]"
            title="Sair da sala"
          >
            <X class="size-3" />
          </button>
        </div>
      </div>
    {/if}

    <!-- ===== IFRAME (always rendered, never destroyed) ===== -->
    <div class="relative flex-1 overflow-hidden">
      <iframe
        bind:this={iframeRef}
        src={coworkSession.appUrl}
        title="Sala Cowork"
        class="h-full w-full border-0"
        allow="camera; microphone; display-capture"
        sandbox="allow-scripts allow-same-origin allow-popups"
      ></iframe>

      <!-- Loading overlay (full mode only) -->
      {#if isFull && !coworkSession.iframeReady}
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
{/if}

<style>
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
