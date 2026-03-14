<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { FileDown, ExternalLink, Code, FileText } from '@lucide/svelte';
  import { browser } from '$app/environment';
  import DOMPurify from 'dompurify';

  /**
   * @typedef {Object} Props
   * @property {string} msgType
   * @property {string} [content]
   * @property {string} [mediaUrl]
   * @property {any} [metadata]
   * @property {string} [contentType]
   */

  /** @type {Props} */
  let { msgType = 'text', content = '', mediaUrl = '', metadata = {}, contentType = 'text' } = $props();

  let showLightbox = $state(false);
  let viewMode = $state('auto'); // 'auto' | 'html' | 'text'

  const PURIFY_CONFIG = {
    ALLOWED_TAGS: ['p', 'br', 'div', 'span', 'a', 'b', 'strong', 'i', 'em', 'u',
                   'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
                   'table', 'thead', 'tbody', 'tr', 'td', 'th', 'img', 'hr',
                   'blockquote', 'pre', 'code', 'font', 'center', 'small', 'sub', 'sup'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'style', 'width', 'height',
                   'align', 'valign', 'color', 'bgcolor', 'border', 'cellpadding',
                   'cellspacing', 'target', 'rel'],
    ADD_ATTR: ['target'],
  };

  // Auto-detect HTML content even when content_type is not set (backward compat)
  let isHtml = $derived(
    contentType === 'html' ||
    (contentType !== 'text' && content && /<[a-z][\s\S]*>/i.test(content))
  );

  let sanitizedHtml = $derived(
    browser && isHtml && content
      ? DOMPurify.sanitize(content, PURIFY_CONFIG)
      : ''
  );

  // Text body from metadata (stored separately by backend) or strip HTML as fallback
  let textBody = $derived(metadata?.text_body || (isHtml ? stripHtml(content) : content));

  // Has both versions available for toggle
  let hasTextVersion = $derived(isHtml && !!(metadata?.text_body || content));

  // Current display mode
  let showAsHtml = $derived(
    isHtml && (viewMode === 'auto' || viewMode === 'html')
  );

  /** @param {string} html */
  function stripHtml(html) {
    if (!html) return '';
    return html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n')
      .replace(/<\/div>/gi, '\n')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#039;/g, "'")
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

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
    // Match URLs but exclude trailing punctuation that's likely not part of the URL
    return escaped.replace(
      /(https?:\/\/[^\s<>&]+(?:&amp;[^\s<>&]+)*)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer" class="underline hover:opacity-80">$1</a>'
    );
  }
</script>

{#if msgType === 'text'}
  {#if showAsHtml && sanitizedHtml}
    <div class="email-html text-sm break-words
      [&_a]:underline [&_a]:text-inherit
      [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded
      [&_table]:w-full [&_table]:border-collapse
      [&_td]:align-top [&_td]:p-1
      [&_th]:align-left [&_th]:p-1 [&_th]:font-semibold
      [&_blockquote]:border-l-2 [&_blockquote]:border-current/20 [&_blockquote]:pl-3 [&_blockquote]:opacity-70 [&_blockquote]:my-2
      [&_h1]:text-base [&_h1]:font-semibold [&_h1]:my-2
      [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:my-1.5
      [&_h3]:text-sm [&_h3]:font-medium [&_h3]:my-1
      [&_p]:my-1
      [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:my-1
      [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:my-1
      [&_li]:my-0.5
      [&_pre]:overflow-x-auto [&_pre]:text-xs [&_pre]:bg-black/5 [&_pre]:p-2 [&_pre]:rounded
      [&_code]:text-xs [&_code]:bg-black/5 [&_code]:px-1 [&_code]:rounded
      [&_hr]:border-current/10 [&_hr]:my-3
      [&_font]:!text-inherit">
      {@html sanitizedHtml}
    </div>
    {#if hasTextVersion}
      <button
        class="flex items-center gap-1 text-[10px] opacity-50 hover:opacity-80 mt-1.5 transition-opacity cursor-pointer"
        onclick={() => viewMode = 'text'}
        title="Ver versão texto"
      >
        <FileText class="size-3" />
        Ver texto
      </button>
    {/if}
  {:else if isHtml && viewMode === 'text'}
    <p class="text-sm whitespace-pre-wrap break-words">{textBody}</p>
    <button
      class="flex items-center gap-1 text-[10px] opacity-50 hover:opacity-80 mt-1.5 transition-opacity cursor-pointer"
      onclick={() => viewMode = 'html'}
      title="Ver versão HTML"
    >
      <Code class="size-3" />
      Ver HTML
    </button>
  {:else}
    <p class="text-sm whitespace-pre-wrap break-words">{@html linkify(content)}</p>
  {/if}

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
