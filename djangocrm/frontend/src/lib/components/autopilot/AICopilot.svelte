<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { assistant } from '$lib/api.js';
  import { Sparkles, Loader2, ChevronDown, ChevronRight, AlertCircle } from '@lucide/svelte';

  /**
   * @type {{
   *   type: 'automation' | 'reminder' | 'campaign',
   *   context?: Record<string, string>,
   *   onGenerated?: (result: any) => void,
   * }}
   */
  let { type = 'automation', context = {}, onGenerated = () => {} } = $props();

  let expanded = $state(false);
  let prompt = $state('');
  let loading = $state(false);
  let error = $state('');
  let notConfigured = $state(false);

  const PLACEHOLDERS = {
    automation: 'Ex: "Quando um lead for criado, enviar notificação para o responsável"',
    reminder: 'Ex: "Lembrar 3 dias antes do vencimento por email ao contato"',
    campaign: 'Ex: "Email de boas-vindas para novos clientes com desconto de 10%"',
  };

  const TITLES = {
    automation: 'Gerar Automação com IA',
    reminder: 'Gerar Lembrete com IA',
    campaign: 'Gerar Conteúdo com IA',
  };

  async function generate() {
    if (!prompt.trim()) return;
    loading = true;
    error = '';
    notConfigured = false;

    try {
      const body = { type, prompt: prompt.trim(), ...context };
      const result = await assistant.aiGenerate(body);

      if (result?.error) {
        if (result.error.includes('não configurada')) {
          notConfigured = true;
        } else {
          error = result.error;
        }
        return;
      }

      onGenerated(result);
      prompt = '';
      expanded = false;
    } catch (err) {
      error = err?.message || 'Erro ao gerar configuração.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="rounded-lg border border-dashed border-purple-300 dark:border-purple-700 bg-purple-50/50 dark:bg-purple-950/20">
  <button
    type="button"
    class="flex w-full items-center justify-between px-4 py-2.5 transition-colors hover:bg-purple-100/50 dark:hover:bg-purple-900/20 rounded-lg"
    onclick={() => (expanded = !expanded)}
  >
    <div class="flex items-center gap-2">
      {#if expanded}
        <ChevronDown class="size-4 text-purple-500" />
      {:else}
        <ChevronRight class="size-4 text-purple-500" />
      {/if}
      <Sparkles class="size-4 text-purple-500" />
      <span class="text-sm font-medium text-purple-700 dark:text-purple-300">{TITLES[type]}</span>
    </div>
  </button>

  {#if expanded}
    <div class="space-y-3 border-t border-purple-200 dark:border-purple-800 px-4 py-3">
      {#if notConfigured}
        <div class="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-3">
          <AlertCircle class="size-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
          <div class="text-xs text-amber-700 dark:text-amber-300">
            <p class="font-medium">IA não configurada</p>
            <p class="mt-0.5">Defina a variável <code class="rounded bg-amber-100 dark:bg-amber-900 px-1">OPENAI_API_KEY</code> nas configurações do servidor para habilitar este recurso.</p>
          </div>
        </div>
      {:else}
        <div>
          <textarea
            bind:value={prompt}
            placeholder={PLACEHOLDERS[type]}
            rows="2"
            maxlength="1000"
            disabled={loading}
            class="border-input bg-background w-full rounded-md border px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-400 dark:focus:ring-purple-600 disabled:opacity-50"
            onkeydown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) generate(); }}
          ></textarea>
          <p class="mt-1 text-[10px] text-muted-foreground">
            {prompt.length}/1000 &middot; Ctrl+Enter para gerar
          </p>
        </div>

        {#if error}
          <div class="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2.5">
            <AlertCircle class="size-4 text-destructive mt-0.5 shrink-0" />
            <p class="text-xs text-destructive">{error}</p>
          </div>
        {/if}

        <div class="flex justify-end">
          <Button
            type="button"
            size="sm"
            class="gap-2 bg-purple-600 hover:bg-purple-700 text-white"
            disabled={!prompt.trim() || loading}
            onclick={generate}
          >
            {#if loading}
              <Loader2 class="size-4 animate-spin" />
              Gerando...
            {:else}
              <Sparkles class="size-4" />
              Gerar com IA
            {/if}
          </Button>
        </div>
      {/if}
    </div>
  {/if}
</div>
