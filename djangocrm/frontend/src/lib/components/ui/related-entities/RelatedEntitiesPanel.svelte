<script>
  import { apiRequest } from '$lib/api.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Collapsible from '$lib/components/ui/collapsible/index.js';
  import { FinancialSummaryCard } from './index.js';
  import { formatCurrency, formatRelativeDate } from '$lib/utils/formatting.js';
  import {
    ChevronRight,
    Target,
    Sparkles,
    Ticket,
    CheckSquare,
    FileText,
    DollarSign,
    MessageSquare,
    Loader2,
    ExternalLink
  } from '@lucide/svelte';

  /**
   * @type {{
   *   contactId?: string,
   *   entityId?: string,
   *   entityType?: 'contact' | 'opportunity' | 'lead' | 'case',
   *   sections?: string[],
   *   class?: string
   * }}
   */
  let {
    contactId,
    entityId,
    entityType = 'contact',
    sections = [],
    class: className = ''
  } = $props();

  /** @type {Record<string, any>} */
  let sectionData = $state({});
  /** @type {Record<string, boolean>} */
  let loadingState = $state({});
  /** @type {Record<string, boolean>} */
  let loadedSections = $state({});

  const SECTION_CONFIG = {
    leads: { icon: Target, title: 'Oportunidades (Leads)', color: 'text-blue-600', path: '/leads' },
    opportunities: { icon: Sparkles, title: 'Negócios', color: 'text-purple-600', path: '/opportunities' },
    cases: { icon: Ticket, title: 'Chamados', color: 'text-orange-600', path: '/cases' },
    tasks: { icon: CheckSquare, title: 'Tarefas', color: 'text-green-600', path: '/tasks' },
    invoices: { icon: FileText, title: 'Faturas', color: 'text-indigo-600', path: '/invoices' },
    financial: { icon: DollarSign, title: 'Financeiro', color: 'text-emerald-600', path: null },
    conversations: { icon: MessageSquare, title: 'Conversas', color: 'text-cyan-600', path: '/conversations' },
    lead: { icon: Target, title: 'Lead de Origem', color: 'text-blue-600', path: '/leads' }
  };

  /**
   * Build API URL based on entity type
   * @param {string} section
   * @returns {string}
   */
  function buildApiUrl(section) {
    if (entityType === 'contact' && contactId) {
      return `/contacts/${contactId}/context/?include=${section}`;
    }
    if (entityId) {
      return `/${entityType === 'opportunity' ? 'opportunities' : entityType + 's'}/${entityId}/related/?include=${section}`;
    }
    return '';
  }

  /**
   * @param {string} section
   */
  async function loadSection(section) {
    if (loadedSections[section] || loadingState[section]) return;
    const url = buildApiUrl(section);
    if (!url) return;

    loadingState[section] = true;
    try {
      const data = await apiRequest(url);
      if (data && !data.error) {
        sectionData = { ...sectionData, ...data };
        loadedSections[section] = true;
      }
    } catch (e) {
      console.error(`Erro ao carregar ${section}:`, e);
    } finally {
      loadingState[section] = false;
    }
  }

  /**
   * @param {string} section
   * @returns {any[]}
   */
  function getItems(section) {
    return sectionData[section] || [];
  }

  /**
   * @param {string} section
   * @returns {number}
   */
  function getCount(section) {
    return sectionData[`${section}_count`] ?? getItems(section).length;
  }

  /**
   * @param {string} section
   * @param {any} item
   * @returns {string}
   */
  function getItemTitle(section, item) {
    switch (section) {
      case 'leads': return item.title || item.name || 'Sem título';
      case 'opportunities': return item.name || 'Sem nome';
      case 'cases': return item.subject || item.name || 'Sem assunto';
      case 'tasks': return item.subject || item.title || 'Sem título';
      case 'invoices': return item.invoice_number || `Fatura #${item.id?.slice(0, 8)}`;
      case 'conversations': return item.contact_name || item.channel || 'Conversa';
      case 'lead': return item.title || item.name || 'Lead';
      default: return item.name || item.title || '';
    }
  }

  /**
   * @param {string} section
   * @param {any} item
   * @returns {string}
   */
  function getItemSubtitle(section, item) {
    switch (section) {
      case 'leads': return item.status || '';
      case 'opportunities':
        return item.amount ? formatCurrency(item.amount) : (item.stage || '');
      case 'cases': return [item.status, item.priority].filter(Boolean).join(' · ');
      case 'tasks':
        return [item.status, item.due_date ? `Venc: ${item.due_date}` : null].filter(Boolean).join(' · ');
      case 'invoices':
        return [item.status, item.amount_due ? formatCurrency(item.amount_due) : null].filter(Boolean).join(' · ');
      case 'conversations':
        return [item.channel, item.last_message_at ? formatRelativeDate(item.last_message_at) : null].filter(Boolean).join(' · ');
      case 'lead': return item.status || '';
      default: return '';
    }
  }

  /**
   * @param {string} section
   * @param {any} item
   * @returns {string}
   */
  function getItemHref(section, item) {
    const config = SECTION_CONFIG[section];
    if (!config?.path) return '#';
    return `${config.path}?view=${item.id}`;
  }
</script>

<div class="space-y-1 {className}">
  {#each sections as section (section)}
    {@const config = SECTION_CONFIG[section]}
    {#if config}
      {#if section === 'financial'}
        <Collapsible.Root
          onOpenChange={(open) => { if (open) loadSection(section); }}
        >
          <Collapsible.Trigger class="flex w-full items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-accent/50 transition-colors">
            <div class="flex items-center gap-2">
              <config.icon class="size-4 {config.color}" />
              <span class="font-medium">{config.title}</span>
            </div>
            <ChevronRight class="size-3.5 text-muted-foreground transition-transform [[data-state=open]>&]:rotate-90" />
          </Collapsible.Trigger>
          <Collapsible.Content>
            <div class="px-2 pb-2">
              {#if loadingState[section]}
                <div class="flex justify-center py-3">
                  <Loader2 class="size-4 animate-spin text-muted-foreground" />
                </div>
              {:else if sectionData.financial}
                <FinancialSummaryCard financial={sectionData.financial} />
              {:else}
                <p class="px-3 py-2 text-xs text-muted-foreground">Sem dados financeiros</p>
              {/if}
            </div>
          </Collapsible.Content>
        </Collapsible.Root>
      {:else}
        <Collapsible.Root
          onOpenChange={(open) => { if (open) loadSection(section); }}
        >
          <Collapsible.Trigger class="flex w-full items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-accent/50 transition-colors">
            <div class="flex items-center gap-2">
              <config.icon class="size-4 {config.color}" />
              <span class="font-medium">{config.title}</span>
              {#if loadedSections[section] && getCount(section) > 0}
                <Badge variant="secondary" class="h-5 px-1.5 text-[10px]">{getCount(section)}</Badge>
              {/if}
            </div>
            <ChevronRight class="size-3.5 text-muted-foreground transition-transform [[data-state=open]>&]:rotate-90" />
          </Collapsible.Trigger>
          <Collapsible.Content>
            <div class="pb-1">
              {#if loadingState[section]}
                <div class="flex justify-center py-3">
                  <Loader2 class="size-4 animate-spin text-muted-foreground" />
                </div>
              {:else if getItems(section).length === 0}
                <p class="px-3 py-2 text-xs text-muted-foreground">Nenhum registro encontrado</p>
              {:else}
                {#each getItems(section) as item (item.id)}
                  <a
                    href={getItemHref(section, item)}
                    class="flex items-center justify-between rounded-md px-3 py-1.5 text-sm hover:bg-accent/50 transition-colors group"
                  >
                    <div class="min-w-0 flex-1">
                      <span class="block truncate text-sm">{getItemTitle(section, item)}</span>
                      {#if getItemSubtitle(section, item)}
                        <span class="block truncate text-xs text-muted-foreground">{getItemSubtitle(section, item)}</span>
                      {/if}
                    </div>
                    <ExternalLink class="size-3 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity ml-2" />
                  </a>
                {/each}
                {#if getCount(section) > getItems(section).length}
                  <a
                    href={SECTION_CONFIG[section]?.path || '#'}
                    class="block px-3 py-1.5 text-xs text-primary hover:underline"
                  >
                    Ver todos ({getCount(section)})
                  </a>
                {/if}
              {/if}
            </div>
          </Collapsible.Content>
        </Collapsible.Root>
      {/if}
    {/if}
  {/each}
</div>
