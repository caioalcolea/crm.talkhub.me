<script>
  import '../../../../app.css';
  import { page } from '$app/state';
</script>

<svelte:head>
  <title>Erro — TalkHub Cowork</title>
  {@html '<style>body{margin:0;padding:0;background:#09090b}</style>'}
</svelte:head>

<div class="flex min-h-dvh w-screen flex-col items-center justify-center bg-zinc-950 px-4 text-center">
  <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-red-500/10">
    <svg class="h-10 w-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
    </svg>
  </div>

  <h1 class="mb-2 text-3xl font-bold text-white">
    {#if page.status === 404}
      Convite não encontrado
    {:else if page.status === 410}
      Convite expirado
    {:else if page.status === 429}
      Muitas tentativas
    {:else}
      Erro {page.status}
    {/if}
  </h1>

  <p class="mb-8 max-w-md text-sm text-zinc-400">
    {page.error?.message || 'Ocorreu um erro ao carregar a sala de cowork.'}
  </p>

  <a
    href="/"
    class="rounded-xl bg-zinc-800 px-6 py-3 text-sm font-medium text-zinc-300 transition hover:bg-zinc-700 hover:text-white"
  >
    Voltar ao início
  </a>
</div>
