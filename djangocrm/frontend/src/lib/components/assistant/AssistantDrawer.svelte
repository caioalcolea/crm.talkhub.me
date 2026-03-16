<script>
  import { Sparkles, X, Send, ChevronLeft, Plus, Trash2, AlertTriangle, Check, XCircle, Loader, Bot, User, Archive } from '@lucide/svelte';
  import { assistantChat } from '$lib/stores/assistant-chat.svelte.js';
  import { browser } from '$app/environment';

  let inputText = $state('');
  let messagesContainer = $state(null);
  let showHistory = $state(false);

  // Auto-scroll to bottom on new messages
  $effect(() => {
    if (messagesContainer && assistantChat.messages.length > 0) {
      requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      });
    }
  });

  // Load sessions when drawer opens
  $effect(() => {
    if (assistantChat.isOpen && browser) {
      assistantChat.loadSessions();
    }
  });

  async function handleSend() {
    const text = inputText.trim();
    if (!text) return;
    inputText = '';
    await assistantChat.sendMessage(text);
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function getRiskBadge(level) {
    if (level === 'none') return { class: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300', label: 'Leitura' };
    if (level === 'low') return { class: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300', label: 'Baixo' };
    if (level === 'medium') return { class: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300', label: 'Médio' };
    return { class: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300', label: 'Alto' };
  }
</script>

<!-- Escape key handler -->
<svelte:window onkeydown={(e) => { if (e.key === 'Escape' && assistantChat.isOpen) assistantChat.close(); }} />

<!-- Floating trigger button -->
{#if !assistantChat.isOpen}
  <button
    onclick={() => assistantChat.open()}
    class="fixed bottom-6 right-6 z-[41] flex h-14 w-14 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg transition-all hover:bg-indigo-700 hover:shadow-xl active:scale-95"
    aria-label="Abrir assistente"
  >
    <Sparkles class="size-6" />
  </button>
{/if}

<!-- Drawer overlay -->
{#if assistantChat.isOpen}
  <!-- Backdrop -->
  <button
    onclick={() => assistantChat.close()}
    class="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
    aria-label="Fechar assistente"
  ></button>

  <!-- Drawer panel -->
  <div class="bg-background fixed bottom-0 right-0 top-0 z-50 flex w-full max-w-md flex-col border-l shadow-2xl sm:w-[420px]">

    <!-- Header -->
    <div class="flex items-center justify-between border-b bg-indigo-600 px-4 py-3 text-white">
      <div class="flex items-center gap-2">
        {#if showHistory}
          <button onclick={() => { showHistory = false; }} class="rounded p-1 hover:bg-indigo-500">
            <ChevronLeft class="size-5" />
          </button>
          <h2 class="text-sm font-semibold">Histórico</h2>
        {:else}
          <Sparkles class="size-5" />
          <h2 class="text-sm font-semibold">TalkHub Autopilot</h2>
        {/if}
      </div>
      <div class="flex items-center gap-1">
        {#if !showHistory}
          <button onclick={() => assistantChat.startNewSession()} class="rounded p-1.5 hover:bg-indigo-500" title="Nova conversa">
            <Plus class="size-4" />
          </button>
          <button onclick={() => { showHistory = true; }} class="rounded p-1.5 hover:bg-indigo-500" title="Histórico">
            <Archive class="size-4" />
          </button>
        {/if}
        <button onclick={() => assistantChat.close()} class="rounded p-1.5 hover:bg-indigo-500">
          <X class="size-4" />
        </button>
      </div>
    </div>

    {#if showHistory}
      <!-- Session history list -->
      <div class="flex-1 overflow-y-auto">
        {#if assistantChat.sessionList.length === 0}
          <div class="text-muted-foreground flex flex-col items-center justify-center gap-2 p-8">
            <Archive class="size-8" />
            <p class="text-sm">Nenhuma conversa anterior</p>
          </div>
        {:else}
          {#each assistantChat.sessionList as session (session.id)}
            <div class="hover:bg-accent flex items-center border-b px-4 py-3">
              <button
                onclick={() => { assistantChat.loadSession(session.id); showHistory = false; }}
                class="flex-1 text-left"
              >
                <p class="text-foreground text-sm font-medium truncate">{session.title || 'Conversa sem título'}</p>
                <p class="text-muted-foreground text-xs">
                  {new Date(session.last_activity_at).toLocaleDateString('pt-BR')} · {session.message_count || 0} msgs
                </p>
              </button>
              <button
                onclick={() => assistantChat.archiveSession(session.id)}
                class="text-muted-foreground ml-2 rounded p-1 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
                title="Arquivar"
              >
                <Trash2 class="size-4" />
              </button>
            </div>
          {/each}
        {/if}
      </div>
    {:else}
      <!-- Chat messages -->
      <div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {#if assistantChat.messages.length === 0}
          <div class="text-muted-foreground flex flex-col items-center justify-center gap-3 py-16">
            <Bot class="size-12 text-indigo-300" />
            <p class="text-center text-sm">
              Olá! Sou o TalkHub Autopilot.<br />
              Como posso ajudar?
            </p>
            <div class="flex flex-wrap justify-center gap-2 mt-2">
              {#each ['Criar lembrete de cobrança', 'Buscar contas vencendo', 'Criar automação de leads'] as suggestion}
                <button
                  onclick={() => { inputText = suggestion; }}
                  class="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs text-indigo-700 hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950 dark:text-indigo-300 dark:hover:bg-indigo-900"
                >
                  {suggestion}
                </button>
              {/each}
            </div>
          </div>
        {/if}

        {#each assistantChat.messages as msg (msg.id)}
          {#if msg.role === 'user'}
            <div class="flex justify-end">
              <div class="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2.5 text-sm text-white">
                {msg.content}
              </div>
            </div>
          {:else if msg.role === 'assistant'}
            <div class="flex gap-2">
              <div class="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900">
                <Bot class="size-4 text-indigo-600 dark:text-indigo-300" />
              </div>
              <div class="bg-muted text-foreground max-w-[85%] rounded-2xl rounded-bl-md px-4 py-2.5 text-sm">
                {msg.content}
              </div>
            </div>
          {:else if msg.role === 'system'}
            <div class="flex justify-center">
              <div class="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-950 dark:text-red-400">
                {msg.content}
              </div>
            </div>
          {:else if msg.role === 'tool_result'}
            <div class="flex justify-center">
              <div class="rounded-lg bg-green-50 px-3 py-2 text-xs text-green-700 dark:bg-green-950 dark:text-green-400">
                {msg.content}
              </div>
            </div>
          {/if}
        {/each}

        <!-- Proposed actions -->
        {#if assistantChat.proposedActions.length > 0}
          <div class="space-y-2 rounded-lg border border-indigo-200 bg-indigo-50 p-3 dark:border-indigo-800 dark:bg-indigo-950">
            <p class="text-xs font-semibold text-indigo-700 dark:text-indigo-300">Ações propostas:</p>
            {#each assistantChat.proposedActions as action, i}
              {@const badge = getRiskBadge(action.risk_level)}
              <div class="bg-background rounded-md border p-3 space-y-2">
                <div class="flex items-center gap-2">
                  <span class="text-foreground text-xs font-medium">{action.tool}</span>
                  <span class="rounded-full px-2 py-0.5 text-[10px] font-medium {badge.class}">{badge.label}</span>
                  {#if action.requires_approval}
                    <span class="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">Requer aprovação</span>
                  {/if}
                </div>
                {#if action.preview}
                  <p class="text-muted-foreground text-xs">{action.preview}</p>
                {/if}
                <div class="flex gap-2">
                  <button
                    onclick={() => assistantChat.confirmAction(i, 'apply')}
                    disabled={assistantChat.isSending}
                    class="flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    <Check class="size-3" /> Aplicar
                  </button>
                  <button
                    onclick={() => assistantChat.confirmAction(i, 'cancel')}
                    disabled={assistantChat.isSending}
                    class="bg-muted text-foreground flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium hover:bg-gray-300 disabled:opacity-50 dark:hover:bg-gray-600"
                  >
                    <XCircle class="size-3" /> Cancelar
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}

        <!-- Sending indicator -->
        {#if assistantChat.isSending}
          <div class="flex gap-2">
            <div class="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900">
              <Loader class="size-4 animate-spin text-indigo-600 dark:text-indigo-300" />
            </div>
            <div class="bg-muted rounded-2xl rounded-bl-md px-4 py-2.5">
              <div class="flex gap-1">
                <div class="bg-muted-foreground h-2 w-2 animate-bounce rounded-full" style="animation-delay: 0ms;"></div>
                <div class="bg-muted-foreground h-2 w-2 animate-bounce rounded-full" style="animation-delay: 150ms;"></div>
                <div class="bg-muted-foreground h-2 w-2 animate-bounce rounded-full" style="animation-delay: 300ms;"></div>
              </div>
            </div>
          </div>
        {/if}
      </div>

      <!-- Input area -->
      <div class="bg-background border-t p-3">
        {#if assistantChat.error && !assistantChat.messages.some(m => m.metadata?.error)}
          <div class="mb-2 flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-950 dark:text-red-400">
            <AlertTriangle class="size-3.5 shrink-0" />
            <span>{assistantChat.error}</span>
          </div>
        {/if}
        <div class="flex items-end gap-2">
          <textarea
            bind:value={inputText}
            onkeydown={handleKeydown}
            placeholder="Digite sua mensagem..."
            rows="1"
            class="border-input bg-background text-foreground placeholder:text-muted-foreground max-h-24 min-h-[40px] flex-1 resize-none rounded-lg border px-3 py-2.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            disabled={assistantChat.isSending}
          ></textarea>
          <button
            onclick={handleSend}
            disabled={!inputText.trim() || assistantChat.isSending}
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:bg-gray-300 disabled:text-gray-500 dark:disabled:bg-gray-700 dark:disabled:text-gray-500"
          >
            {#if assistantChat.isSending}
              <Loader class="size-4 animate-spin" />
            {:else}
              <Send class="size-4" />
            {/if}
          </button>
        </div>
      </div>
    {/if}
  </div>
{/if}
