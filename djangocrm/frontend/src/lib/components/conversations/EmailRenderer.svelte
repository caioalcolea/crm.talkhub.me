<script>
  import { browser } from '$app/environment';
  import DOMPurify from 'dompurify';
  import { FileText, Code } from '@lucide/svelte';

  /** @type {{ htmlContent: string, textBody?: string }} */
  let { htmlContent = '', textBody = '' } = $props();

  let viewMode = $state('html');
  /** @type {HTMLIFrameElement|null} */
  let iframeEl = $state(null);

  const PURIFY_CONFIG = {
    WHOLE_DOCUMENT: true,
    ADD_TAGS: ['style', 'head', 'meta', 'link'],
    FORBID_TAGS: ['script', 'form', 'audio', 'video', 'object', 'embed', 'iframe'],
    ADD_ATTR: ['target'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
  };

  // SSR-safe: DOMPurify.sanitize is undefined in Node.js
  let sanitizedHtml = $derived(
    browser && htmlContent
      ? DOMPurify.sanitize(htmlContent, PURIFY_CONFIG)
      : ''
  );

  // WHOLE_DOCUMENT: true means sanitizedHtml is already a full <html>...</html> document.
  // Prepend base styles — the browser moves <base> and <style> into <head> automatically.
  let iframeSrcDoc = $derived(
    sanitizedHtml
      ? `<base target="_blank"><style>body{margin:0;padding:8px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;line-height:1.5;color:#1a1a1a;word-wrap:break-word;overflow-wrap:break-word}img{max-width:100%;height:auto}table{max-width:100%}a{color:#2563eb}pre{overflow-x:auto}</style>${sanitizedHtml}`
      : ''
  );

  let plainText = $derived(textBody || stripHtml(htmlContent));

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

  function handleIframeLoad() {
    if (!iframeEl) return;
    try {
      const doc = iframeEl.contentWindow?.document;
      if (!doc) return;
      const height = Math.max(
        doc.body?.scrollHeight || 0, doc.body?.offsetHeight || 0,
        doc.documentElement?.clientHeight || 0, doc.documentElement?.scrollHeight || 0
      );
      iframeEl.style.height = `${Math.min(Math.max(height, 60), 600)}px`;
    } catch {
      iframeEl.style.height = '300px';
    }
  }
</script>

{#if viewMode === 'html' && sanitizedHtml}
  <div class="w-full overflow-hidden rounded-md border border-current/10 bg-white">
    <iframe
      bind:this={iframeEl}
      srcdoc={iframeSrcDoc}
      sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin"
      title="Conteudo do Email"
      class="w-full border-none block min-h-[60px]"
      scrolling="auto"
      onload={handleIframeLoad}
    ></iframe>
  </div>
  <button
    class="flex items-center gap-1 text-[10px] opacity-50 hover:opacity-80 mt-1.5 transition-opacity cursor-pointer"
    onclick={() => viewMode = 'text'}
    title="Ver versao texto"
  >
    <FileText class="size-3" />
    Ver texto
  </button>
{:else}
  <p class="text-sm whitespace-pre-wrap break-words">{plainText}</p>
  {#if sanitizedHtml}
    <button
      class="flex items-center gap-1 text-[10px] opacity-50 hover:opacity-80 mt-1.5 transition-opacity cursor-pointer"
      onclick={() => viewMode = 'html'}
      title="Ver versao HTML"
    >
      <Code class="size-3" />
      Ver HTML
    </button>
  {/if}
{/if}
