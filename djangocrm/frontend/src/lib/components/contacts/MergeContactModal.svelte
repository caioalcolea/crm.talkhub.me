<script>
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import ContactAutocomplete from './ContactAutocomplete.svelte';
  import { apiRequest } from '$lib/api.js';
  import { toast } from 'svelte-sonner';
  import { Loader2, AlertTriangle, ArrowRight, User, MessageSquare, GitMerge, Mail, Phone, MapPin } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {boolean} open
   * @property {any} primaryContact - The contact to keep
   * @property {any[]} [suggestedDuplicates] - Pre-loaded duplicates
   * @property {(() => void)} [onClose]
   * @property {((mergedContact: any, stats: any) => void)} [onMerged]
   */

  /** @type {Props} */
  let {
    open = $bindable(false),
    primaryContact,
    suggestedDuplicates = [],
    onClose,
    onMerged
  } = $props();

  /** @type {any} */
  let secondaryContact = $state(null);
  let preview = $state(null);
  let loadingPreview = $state(false);
  let merging = $state(false);

  // Reset when modal opens/closes
  $effect(() => {
    if (!open) {
      secondaryContact = null;
      preview = null;
      loadingPreview = false;
      merging = false;
    }
  });

  // Load preview when secondary is selected
  $effect(() => {
    if (secondaryContact && primaryContact) {
      loadPreview();
    } else {
      preview = null;
    }
  });

  async function loadPreview() {
    if (!secondaryContact || !primaryContact) return;
    loadingPreview = true;
    try {
      const result = await apiRequest('/contacts/merge/preview/', {
        method: 'POST',
        body: {
          primary_id: primaryContact.id,
          secondary_id: secondaryContact.id
        }
      });
      preview = result;
    } catch (e) {
      toast.error('Erro ao gerar preview do merge');
      preview = null;
    } finally {
      loadingPreview = false;
    }
  }

  async function executeMerge() {
    if (!secondaryContact || !primaryContact) return;
    merging = true;
    try {
      const result = await apiRequest('/contacts/merge/', {
        method: 'POST',
        body: {
          primary_id: primaryContact.id,
          secondary_id: secondaryContact.id
        }
      });
      if (result.error) {
        toast.error(result.message || 'Erro ao mesclar contatos');
      } else {
        toast.success('Contatos mesclados com sucesso!');
        onMerged?.(result.contact, result.stats);
        open = false;
      }
    } catch (e) {
      toast.error('Erro ao mesclar contatos');
    } finally {
      merging = false;
    }
  }

  /** @param {any} dup */
  function selectDuplicate(dup) {
    secondaryContact = dup;
  }

  /** @param {any} contact */
  function handleAutocompleteSelect(contact) {
    if (contact.id === primaryContact?.id) {
      toast.error('Não é possível mesclar um contato consigo mesmo');
      return;
    }
    secondaryContact = contact;
  }

  /**
   * @param {string} field
   */
  function fieldLabel(field) {
    const labels = {
      first_name: 'Nome', last_name: 'Sobrenome',
      email: 'E-mail', phone: 'Telefone',
      organization: 'Empresa', title: 'Cargo', department: 'Departamento',
      linkedin_url: 'LinkedIn', instagram: 'Instagram', facebook: 'Facebook',
      tiktok: 'TikTok', telegram: 'Telegram',
      address_line: 'Endereço', city: 'Cidade', state: 'Estado',
      postcode: 'CEP', country: 'País',
      source: 'Origem', description: 'Observações',
      talkhub_channel_type: 'Canal TalkHub', talkhub_channel_id: 'ID Canal TalkHub',
      talkhub_subscriber_id: 'Subscriber ID', omni_user_ns: 'Omni NS',
      account_id: 'Empresa (FK)',
    };
    return labels[field] || field;
  }

  /** @param {string} reason */
  function reasonLabel(reason) {
    const labels = {
      email: 'Mesmo e-mail', phone: 'Mesmo telefone', name: 'Mesmo nome',
      chatwoot_id: 'Mesmo Chatwoot ID', talkhub_subscriber_id: 'Mesmo TalkHub ID',
      omni_user_ns: 'Mesmo Omni NS',
    };
    return labels[reason] || reason;
  }

  function contactDisplayName(c) {
    if (!c) return '';
    const name = `${c.first_name || c.firstName || ''} ${c.last_name || c.lastName || ''}`.trim();
    return name || c.email || c.phone || 'Sem nome';
  }

  function contactSubline(c) {
    if (!c) return '';
    const parts = [];
    if (c.email) parts.push(c.email);
    if (c.phone) parts.push(c.phone);
    if (c.organization) parts.push(c.organization);
    return parts.join(' · ');
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="max-w-2xl max-h-[85vh] overflow-y-auto">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2">
        <GitMerge class="h-5 w-5" />
        Mesclar Contatos
      </Dialog.Title>
      <Dialog.Description>
        Unifique dois contatos em um só. Todas as conversas, leads e entidades serão movidas.
      </Dialog.Description>
    </Dialog.Header>

    <div class="space-y-4 py-2">
      <!-- Primary contact card -->
      <div>
        <p class="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Contato principal (mantido)
        </p>
        <div class="flex items-center gap-3 rounded-lg border bg-muted/30 p-3">
          <div class="flex size-9 items-center justify-center rounded-full bg-primary/10 text-primary">
            <User class="size-4" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium truncate">{contactDisplayName(primaryContact)}</p>
            <p class="text-xs text-muted-foreground truncate">{contactSubline(primaryContact)}</p>
          </div>
        </div>
      </div>

      <!-- Secondary contact selection -->
      <div>
        <p class="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Contato a ser absorvido
        </p>

        {#if !secondaryContact}
          <!-- Suggested duplicates -->
          {#if suggestedDuplicates.length > 0}
            <div class="mb-2 space-y-1">
              {#each suggestedDuplicates as dup (dup.id)}
                <button
                  type="button"
                  class="flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors hover:bg-accent"
                  onclick={() => selectDuplicate(dup)}
                >
                  <div class="flex size-8 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                    <User class="size-3.5" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <p class="text-sm font-medium truncate">
                      {dup.first_name || ''} {dup.last_name || ''}
                    </p>
                    <p class="text-xs text-muted-foreground truncate">
                      {[dup.email, dup.phone].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  <div class="flex flex-wrap gap-1">
                    {#each dup.match_reasons || [] as reason}
                      <Badge variant="secondary" class="text-[10px] px-1.5 py-0">
                        {reasonLabel(reason)}
                      </Badge>
                    {/each}
                  </div>
                  {#if dup.conversations_count > 0}
                    <div class="flex items-center gap-1 text-xs text-muted-foreground">
                      <MessageSquare class="size-3" />
                      {dup.conversations_count}
                    </div>
                  {/if}
                </button>
              {/each}
            </div>
            <p class="mb-1.5 text-xs text-muted-foreground">ou buscar outro contato:</p>
          {/if}

          <ContactAutocomplete
            onSelect={handleAutocompleteSelect}
            placeholder="Buscar contato para mesclar..."
          />
        {:else}
          <!-- Selected secondary -->
          <div class="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/30">
            <div class="flex size-9 items-center justify-center rounded-full bg-amber-200 text-amber-700 dark:bg-amber-900 dark:text-amber-400">
              <User class="size-4" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium truncate">{contactDisplayName(secondaryContact)}</p>
              <p class="text-xs text-muted-foreground truncate">{contactSubline(secondaryContact)}</p>
            </div>
            <Button variant="ghost" size="sm" onclick={() => (secondaryContact = null)}>
              Alterar
            </Button>
          </div>
        {/if}
      </div>

      <!-- Preview -->
      {#if loadingPreview}
        <div class="flex items-center justify-center py-6">
          <Loader2 class="size-5 animate-spin text-muted-foreground" />
          <span class="ml-2 text-sm text-muted-foreground">Gerando preview...</span>
        </div>
      {:else if preview}
        <!-- Field-by-field preview -->
        <div>
          <p class="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Resultado da mesclagem
          </p>
          <div class="rounded-lg border">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b bg-muted/50">
                  <th class="px-3 py-1.5 text-left text-xs font-medium text-muted-foreground">Campo</th>
                  <th class="px-3 py-1.5 text-left text-xs font-medium text-muted-foreground">Resultado</th>
                  <th class="px-3 py-1.5 text-left text-xs font-medium text-muted-foreground">Origem</th>
                </tr>
              </thead>
              <tbody>
                {#each Object.entries(preview.merged_preview || {}) as [field, info] (field)}
                  {#if info.value}
                    <tr class="border-b last:border-0">
                      <td class="px-3 py-1.5 text-xs text-muted-foreground whitespace-nowrap">
                        {fieldLabel(field)}
                      </td>
                      <td class="px-3 py-1.5 text-xs truncate max-w-[200px]" title={info.value}>
                        {info.value?.length > 50 ? info.value.slice(0, 50) + '...' : info.value}
                      </td>
                      <td class="px-3 py-1.5">
                        {#if info.source === 'secondary'}
                          <Badge variant="outline" class="text-[10px] px-1.5 py-0 text-amber-600 border-amber-300">
                            <ArrowRight class="mr-0.5 size-2.5" />
                            Absorvido
                          </Badge>
                        {:else if info.source === 'concatenado'}
                          <Badge variant="outline" class="text-[10px] px-1.5 py-0 text-blue-600 border-blue-300">
                            Mesclado
                          </Badge>
                        {:else}
                          <span class="text-[10px] text-muted-foreground">Principal</span>
                        {/if}
                      </td>
                    </tr>
                  {/if}
                {/each}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Entities to move -->
        {#if Object.values(preview.entities_to_move || {}).some(v => v > 0)}
          <div>
            <p class="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Entidades a mover
            </p>
            <div class="flex flex-wrap gap-2">
              {#each Object.entries(preview.entities_to_move || {}) as [key, count]}
                {#if count > 0}
                  <Badge variant="secondary" class="gap-1">
                    {count}
                    {key === 'conversations' ? 'conversas' :
                     key === 'invoices' ? 'faturas' :
                     key === 'estimates' ? 'orçamentos' :
                     key === 'orders' ? 'pedidos' :
                     key === 'leads' ? 'leads' :
                     key === 'opportunities' ? 'oportunidades' :
                     key === 'cases' ? 'casos' :
                     key === 'tasks' ? 'tarefas' : key}
                  </Badge>
                {/if}
              {/each}
            </div>
          </div>
        {/if}

        <!-- Channels unified -->
        {#if preview.channels_unified?.length > 0}
          <div class="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Canais unificados:</span>
            {#each preview.channels_unified as ch}
              <Badge variant="outline" class="text-[10px]">{ch}</Badge>
            {/each}
          </div>
        {/if}

        <!-- Data preservation info -->
        {@const priEmail = primaryContact?.email}
        {@const secEmail = secondaryContact?.email}
        {@const priPhone = primaryContact?.phone}
        {@const secPhone = secondaryContact?.phone}
        {@const hasConflictingEmail = priEmail && secEmail && priEmail.toLowerCase() !== secEmail.toLowerCase()}
        {@const hasConflictingPhone = priPhone && secPhone && priPhone !== secPhone}
        {#if hasConflictingEmail || hasConflictingPhone}
          <div class="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-950/30">
            <Mail class="mt-0.5 size-4 shrink-0 text-blue-600 dark:text-blue-400" />
            <div class="text-xs text-blue-700 dark:text-blue-300">
              <p class="font-medium">Dados preservados como adicionais:</p>
              <ul class="mt-1 list-inside list-disc space-y-0.5">
                {#if hasConflictingEmail}
                  <li>E-mail <strong>{secEmail}</strong> será adicionado como e-mail adicional</li>
                {/if}
                {#if hasConflictingPhone}
                  <li>Telefone <strong>{secPhone}</strong> será adicionado como telefone adicional</li>
                {/if}
              </ul>
            </div>
          </div>
        {/if}

        <!-- Warning -->
        <div class="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
          <AlertTriangle class="mt-0.5 size-4 shrink-0 text-destructive" />
          <p class="text-xs text-destructive">
            <strong>{contactDisplayName(secondaryContact)}</strong> será excluído permanentemente.
            Esta ação não pode ser desfeita.
          </p>
        </div>
      {/if}
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => { open = false; onClose?.(); }} disabled={merging}>
        Cancelar
      </Button>
      <Button
        onclick={executeMerge}
        disabled={!secondaryContact || !preview || merging || loadingPreview}
        class="gap-1.5"
      >
        {#if merging}
          <Loader2 class="size-4 animate-spin" />
          Mesclando...
        {:else}
          <GitMerge class="size-4" />
          Mesclar Contatos
        {/if}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
