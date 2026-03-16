<script>
  import { assistant } from '$lib/api.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Loader2, Sparkles } from '@lucide/svelte';

  let { moduleKey = '', onSelect = () => {} } = $props();

  let presets = $state([]);
  let loading = $state(true);

  $effect(() => {
    if (moduleKey) {
      loadPresets();
    }
  });

  async function loadPresets() {
    loading = true;
    try {
      const data = await assistant.presets(moduleKey);
      presets = Array.isArray(data) ? data : (data?.results || []);
    } catch {
      presets = [];
    } finally {
      loading = false;
    }
  }
</script>

<div class="space-y-3">
  <p class="text-muted-foreground text-xs font-medium">Presets disponíveis</p>

  {#if loading}
    <div class="flex items-center justify-center py-4">
      <Loader2 class="size-5 animate-spin text-muted-foreground" />
    </div>
  {:else if presets.length === 0}
    <p class="text-muted-foreground text-xs italic py-2">Nenhum preset disponível para este módulo.</p>
  {:else}
    <div class="grid gap-2 sm:grid-cols-2">
      {#each presets as preset}
        <div class="flex flex-col justify-between rounded-md border p-3 space-y-2">
          <div>
            <div class="flex items-center gap-1.5">
              <Sparkles class="size-3.5 text-amber-500" />
              <span class="text-sm font-medium">{preset.name}</span>
            </div>
            {#if preset.description}
              <p class="text-muted-foreground text-xs mt-1">{preset.description}</p>
            {/if}
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="self-end text-xs h-7"
            onclick={() => onSelect(preset.key || preset.name, preset.config || preset)}
          >Aplicar</Button>
        </div>
      {/each}
    </div>
  {/if}
</div>
