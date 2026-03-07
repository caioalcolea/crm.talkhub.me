<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { FileDown, ExternalLink } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {string} msgType
   * @property {string} [content]
   * @property {string} [mediaUrl]
   * @property {any} [metadata]
   */

  /** @type {Props} */
  let { msgType = 'text', content = '', mediaUrl = '', metadata = {} } = $props();

  let showLightbox = $state(false);

  /** @param {string} text */
  function escapeHtml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /** @param {string} text */
  function linkify(text) {
    if (!text) return '';
    const escaped = escapeHtml(text);
    return escaped.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" rel="noopener" class="underline hover:opacity-80">$1</a>'
    );
  }
</script>

{#if msgType === 'text'}
  <p class="text-sm whitespace-pre-wrap break-words">{@html linkify(content)}</p>

{:else if msgType === 'image'}
  {#if mediaUrl}
    <button class="block cursor-pointer" onclick={() => showLightbox = true}>
      <img
        src={mediaUrl}
        alt="Imagem"
        class="max-w-full max-h-60 rounded-lg object-cover"
        loading="lazy"
      />
    </button>
    {#if content}
      <p class="text-sm mt-1 whitespace-pre-wrap">{content}</p>
    {/if}

    <!-- Lightbox -->
    {#if showLightbox}
      <button
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
        onclick={() => showLightbox = false}
      >
        <img src={mediaUrl} alt="Imagem ampliada" class="max-h-[90vh] max-w-[90vw] rounded-lg" />
      </button>
    {/if}
  {/if}

{:else if msgType === 'video'}
  {#if mediaUrl}
    <!-- svelte-ignore a11y_media_has_caption -->
    <video controls class="max-w-full max-h-60 rounded-lg" preload="metadata">
      <source src={mediaUrl} />
    </video>
    {#if content}
      <p class="text-sm mt-1">{content}</p>
    {/if}
  {/if}

{:else if msgType === 'audio'}
  {#if mediaUrl}
    <audio controls class="w-full max-w-xs" preload="metadata">
      <source src={mediaUrl} />
    </audio>
    {#if content}
      <p class="text-sm mt-1">{content}</p>
    {/if}
  {/if}

{:else if msgType === 'file'}
  {#if mediaUrl}
    <a
      href={mediaUrl}
      target="_blank"
      rel="noopener"
      class="flex items-center gap-2 rounded-lg border bg-background/50 px-3 py-2 text-sm hover:bg-background transition-colors"
    >
      <FileDown class="size-5 shrink-0" />
      <span class="truncate flex-1">{content || 'Arquivo'}</span>
      <ExternalLink class="size-3.5 shrink-0 opacity-50" />
    </a>
  {:else}
    <p class="text-sm">{content}</p>
  {/if}

{:else if msgType === 'payload'}
  <!-- Structured card -->
  <div class="rounded-lg border bg-background/50 p-3 space-y-2">
    {#if metadata?.title}
      <p class="text-sm font-medium">{metadata.title}</p>
    {/if}
    {#if metadata?.description || content}
      <p class="text-xs text-muted-foreground">{metadata?.description || content}</p>
    {/if}
    {#if metadata?.buttons?.length}
      <div class="flex flex-wrap gap-1.5 pt-1">
        {#each metadata.buttons as btn}
          <Button variant="outline" size="sm" class="text-xs h-7">
            {btn.label || btn.text || 'Ação'}
          </Button>
        {/each}
      </div>
    {/if}
  </div>

{:else}
  <p class="text-sm whitespace-pre-wrap">{content}</p>
{/if}
