<script>
  import { goto, invalidateAll } from '$app/navigation';
  import { enhance } from '$app/forms';
  import { tick } from 'svelte';
  import { toast } from 'svelte-sonner';

  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Textarea } from '$lib/components/ui/textarea';
  import * as Select from '$lib/components/ui/select';
  import * as Card from '$lib/components/ui/card';
  import { Separator } from '$lib/components/ui/separator';
  import { formatCurrency } from '$lib/utils/formatting.js';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';
  import { COUNTRIES } from '$lib/constants/countries.js';
  import { orgSettings } from '$lib/stores/org.js';
  import {
    ArrowLeft,
    Plus,
    Trash2,
    Send,
    Save,
    Eye,
    FileText,
    Building2,
    User,
    Calendar,
    Hash
  } from '@lucide/svelte';

  /** @type {{ data: import('./$types').PageData }} */
  let { data } = $props();

  // Get default template for pre-populating notes/terms
  const template = $derived(data.template);

  // Currency options with search
  const currencyOptions = CURRENCY_CODES.filter((c) => c.value);
  let currencySearch = $state('');
  const filteredCurrencyOptions = $derived(
    currencySearch
      ? currencyOptions.filter((c) => c.label.toLowerCase().includes(currencySearch.toLowerCase()))
      : currencyOptions
  );

  // Country options with search
  let countrySearch = $state('');
  const filteredCountryOptions = $derived(
    countrySearch
      ? COUNTRIES.filter((c) => c.name.toLowerCase().includes(countrySearch.toLowerCase()))
      : COUNTRIES
  );

  // Payment terms options
  const PAYMENT_TERMS = [
    { value: 'DUE_ON_RECEIPT', label: 'À Vista' },
    { value: 'NET_15', label: 'Net 15' },
    { value: 'NET_30', label: 'Net 30' },
    { value: 'NET_45', label: 'Net 45' },
    { value: 'NET_60', label: 'Net 60' },
    { value: 'CUSTOM', label: 'Personalizado' }
  ];

  // Form state
  let invoice = $state({
    invoiceTitle: '',
    status: 'Draft',
    accountId: '',
    contactId: '',
    currency: $orgSettings.default_currency || 'BRL',
    paymentTerms: 'NET_30',
    issueDate: new Date().toISOString().split('T')[0],
    dueDate: '',
    // Client details (auto-filled from contact)
    clientName: '',
    clientEmail: '',
    clientPhone: '',
    clientAddressLine: '',
    clientCity: '',
    clientState: '',
    clientPostcode: '',
    clientCountry: '',
    // Notes
    notes: '',
    terms: '',
    // Additional metadata
    billingPeriod: '',
    poNumber: ''
  });

  // Line items
  /** @type {Array<{id: string, name: string, description: string, quantity: number, rate: number, amount: number}>} */
  let lineItems = $state([
    { id: crypto.randomUUID(), name: '', description: '', quantity: 1, rate: 0, amount: 0 }
  ]);

  // Form refs
  let createForm;
  let isSaving = $state(false);

  // Derived: accounts and contacts from data
  const accounts = $derived(data.accounts || []);
  const contacts = $derived(data.contacts || []);

  // Derived: filtered contacts based on selected account
  const filteredContacts = $derived(
    invoice.accountId
      ? contacts.filter((c) => c.accountId === invoice.accountId || !c.accountId)
      : contacts
  );

  // Derived: Calculate totals
  const subtotal = $derived(lineItems.reduce((sum, item) => sum + item.quantity * item.rate, 0));
  let taxRate = $state(0);
  const taxAmount = $derived(subtotal * (taxRate / 100));
  const total = $derived(subtotal + taxAmount);

  // Calculate due date based on payment terms
  function calculateDueDate(issueDate, terms) {
    if (!issueDate) return '';
    const date = new Date(issueDate);
    switch (terms) {
      case 'DUE_ON_RECEIPT':
        return issueDate;
      case 'NET_15':
        date.setDate(date.getDate() + 15);
        break;
      case 'NET_30':
        date.setDate(date.getDate() + 30);
        break;
      case 'NET_45':
        date.setDate(date.getDate() + 45);
        break;
      case 'NET_60':
        date.setDate(date.getDate() + 60);
        break;
      default:
        return '';
    }
    return date.toISOString().split('T')[0];
  }

  // Auto-update due date when issue date or payment terms change
  $effect(() => {
    if (invoice.paymentTerms !== 'CUSTOM') {
      invoice.dueDate = calculateDueDate(invoice.issueDate, invoice.paymentTerms);
    }
  });

  // Pre-populate notes and terms from default template (only on initial mount)
  let templateApplied = $state(false);
  $effect(() => {
    if (!templateApplied && template) {
      if (template.defaultNotes && !invoice.notes) {
        invoice.notes = template.defaultNotes;
      }
      if (template.defaultTerms && !invoice.terms) {
        invoice.terms = template.defaultTerms;
      }
      templateApplied = true;
    }
  });

  // Update line item amount when quantity or rate changes
  function updateLineItemAmount(index) {
    lineItems[index].amount = lineItems[index].quantity * lineItems[index].rate;
  }

  // Add new line item
  function addLineItem() {
    lineItems = [
      ...lineItems,
      { id: crypto.randomUUID(), name: '', description: '', quantity: 1, rate: 0, amount: 0 }
    ];
  }

  // Remove line item
  function removeLineItem(index) {
    if (lineItems.length > 1) {
      lineItems = lineItems.filter((_, i) => i !== index);
    }
  }

  // Handle account selection - auto-fill client info
  function handleAccountChange(accountId) {
    invoice.accountId = accountId;
    const account = accounts.find((a) => a.id === accountId);
    if (account) {
      invoice.clientName = account.name || '';
      // Could also populate address from account if available
    }
  }

  // Handle contact selection - auto-fill client email/phone
  function handleContactChange(contactId) {
    invoice.contactId = contactId;
    const contact = contacts.find((c) => c.id === contactId);
    if (contact) {
      invoice.clientEmail = contact.email || '';
      invoice.clientPhone = contact.phone || '';
      if (!invoice.clientName) {
        invoice.clientName = contact.name || '';
      }
    }
  }

  // Validate line items - at least one with name/description and rate > 0
  function hasValidLineItems() {
    return lineItems.some((item) => (item.name || item.description) && item.rate > 0);
  }

  // Save as draft
  async function saveDraft() {
    if (!invoice.accountId || !invoice.contactId) {
      toast.error('Por favor, selecione uma Conta e um Contato');
      return;
    }
    if (!hasValidLineItems()) {
      toast.error('Adicione pelo menos um item com nome/descrição e valor');
      return;
    }
    isSaving = true;
    invoice.status = 'Draft';
    await tick();
    createForm.requestSubmit();
  }

  // Send invoice
  async function sendInvoice() {
    if (!invoice.accountId || !invoice.contactId) {
      toast.error('Por favor, selecione uma Conta e um Contato');
      return;
    }
    if (!hasValidLineItems()) {
      toast.error('Adicione pelo menos um item com nome/descrição e valor');
      return;
    }
    isSaving = true;
    invoice.status = 'Sent';
    await tick();
    createForm.requestSubmit();
  }

  // Go back to list
  function goBack() {
    goto('/invoices');
  }
</script>

<svelte:head>
  <title>Nova Fatura | TalkHub CRM</title>
</svelte:head>

<!-- Hidden Form -->
<form
  bind:this={createForm}
  method="POST"
  action="?/create"
  class="hidden"
  use:enhance={() => {
    return async ({ result }) => {
      isSaving = false;
      if (result.type === 'success') {
        toast.success(
          invoice.status === 'Sent' ? 'Fatura criada e enviada' : 'Fatura salva como rascunho'
        );
        goto('/invoices');
      } else if (result.type === 'failure') {
        toast.error(/** @type {string} */ (result.data?.error) || 'Falha ao criar fatura');
      }
    };
  }}
>
  <input type="hidden" name="invoiceTitle" value={invoice.invoiceTitle} />
  <input type="hidden" name="status" value={invoice.status} />
  <input type="hidden" name="accountId" value={invoice.accountId} />
  <input type="hidden" name="contactId" value={invoice.contactId} />
  <input type="hidden" name="currency" value={invoice.currency} />
  <input type="hidden" name="paymentTerms" value={invoice.paymentTerms} />
  <input type="hidden" name="issueDate" value={invoice.issueDate} />
  <input type="hidden" name="dueDate" value={invoice.dueDate} />
  <input type="hidden" name="clientName" value={invoice.clientName} />
  <input type="hidden" name="clientEmail" value={invoice.clientEmail} />
  <input type="hidden" name="clientPhone" value={invoice.clientPhone} />
  <input type="hidden" name="clientAddressLine" value={invoice.clientAddressLine} />
  <input type="hidden" name="clientCity" value={invoice.clientCity} />
  <input type="hidden" name="clientState" value={invoice.clientState} />
  <input type="hidden" name="clientPostcode" value={invoice.clientPostcode} />
  <input type="hidden" name="clientCountry" value={invoice.clientCountry} />
  <input type="hidden" name="taxRate" value={taxRate} />
  <input type="hidden" name="notes" value={invoice.notes} />
  <input type="hidden" name="terms" value={invoice.terms} />
  <input type="hidden" name="billingPeriod" value={invoice.billingPeriod} />
  <input type="hidden" name="poNumber" value={invoice.poNumber} />
  <input
    type="hidden"
    name="lineItems"
    value={JSON.stringify(
      lineItems.filter((item) => item.name || item.description || item.rate > 0)
    )}
  />
</form>

<div class="bg-muted/30 min-h-screen">
  <!-- Header -->
  <div class="bg-background sticky top-0 z-10 border-b">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
      <div class="flex items-center gap-4">
        <Button variant="ghost" size="icon" onclick={goBack}>
          <ArrowLeft class="size-5" />
        </Button>
        <div>
          <h1 class="text-xl font-semibold">Nova Fatura</h1>
          <p class="text-muted-foreground text-sm">Crie uma nova fatura para o seu cliente</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <Button variant="outline" onclick={saveDraft} disabled={isSaving}>
          <Save class="mr-2 size-4" />
          Salvar Rascunho
        </Button>
        <Button onclick={sendInvoice} disabled={isSaving}>
          <Send class="mr-2 size-4" />
          Criar Fatura
        </Button>
      </div>
    </div>
  </div>

  <!-- Invoice Editor -->
  <div class="mx-auto max-w-6xl px-6 py-8">
    <div class="bg-background rounded-lg border shadow-sm">
      <!-- Invoice Header -->
      <div class="border-b p-6">
        <div class="flex items-start justify-between">
          <!-- Invoice Title & Number -->
          <div class="space-y-4">
            <div class="text-primary flex items-center gap-2 text-2xl font-bold">
              <FileText class="size-8" />
              <span>FATURA</span>
            </div>
            <div class="space-y-2">
              <div class="flex items-center gap-2">
                <Label class="text-muted-foreground w-24">Fatura #</Label>
                <span class="text-muted-foreground font-medium">Gerado automaticamente</span>
              </div>
              <div class="flex items-center gap-2">
                <Label class="text-muted-foreground w-24">Título</Label>
                <Input
                  bind:value={invoice.invoiceTitle}
                  placeholder="Título da fatura (opcional)"
                  class="max-w-xs"
                />
              </div>
              <div class="flex items-center gap-2">
                <Label class="text-muted-foreground w-24">Pedido de Compra</Label>
                <Input
                  bind:value={invoice.poNumber}
                  placeholder="Pedido de Compra #"
                  class="max-w-xs"
                />
              </div>
              <div class="flex items-center gap-2">
                <Label class="text-muted-foreground w-24">Período de Faturamento</Label>
                <Input
                  bind:value={invoice.billingPeriod}
                  placeholder="ex. Dezembro 2024"
                  class="max-w-xs"
                />
              </div>
            </div>
          </div>

          <!-- Currency & Dates -->
          <div class="space-y-3 text-right">
            <div class="flex items-center justify-end gap-2">
              <Label class="text-muted-foreground">Moeda</Label>
              <Select.Root
                type="single"
                value={invoice.currency}
                onValueChange={(v) => { invoice.currency = v; currencySearch = ''; }}
                onOpenChange={(open) => { if (!open) currencySearch = ''; }}
              >
                <Select.Trigger class="w-48">
                  {currencyOptions.find((c) => c.value === invoice.currency)?.label || 'Buscar moeda...'}
                </Select.Trigger>
                <Select.Content class="max-h-60">
                  <div class="sticky top-0 bg-[var(--surface-raised)] p-2">
                    <Input
                      type="text"
                      placeholder="Buscar moeda..."
                      bind:value={currencySearch}
                      class="h-8 text-sm"
                      onclick={(e) => e.stopPropagation()}
                      onkeydown={(e) => e.stopPropagation()}
                    />
                  </div>
                  {#each filteredCurrencyOptions as option}
                    <Select.Item value={option.value}>{option.label}</Select.Item>
                  {/each}
                  {#if filteredCurrencyOptions.length === 0}
                    <div class="px-3 py-2 text-sm text-gray-500">Nenhuma moeda encontrada</div>
                  {/if}
                </Select.Content>
              </Select.Root>
            </div>
            <div class="flex items-center justify-end gap-2">
              <Label class="text-muted-foreground">Data de Emissão</Label>
              <Input type="date" bind:value={invoice.issueDate} class="w-40" />
            </div>
            <div class="flex items-center justify-end gap-2">
              <Label class="text-muted-foreground">Data de Vencimento</Label>
              <Input type="date" bind:value={invoice.dueDate} class="w-40" />
            </div>
            <div class="flex items-center justify-end gap-2">
              <Label class="text-muted-foreground">Termos</Label>
              <Select.Root
                type="single"
                value={invoice.paymentTerms}
                onValueChange={(v) => (invoice.paymentTerms = v)}
              >
                <Select.Trigger class="w-40">
                  {PAYMENT_TERMS.find((t) => t.value === invoice.paymentTerms)?.label || 'Selecionar'}
                </Select.Trigger>
                <Select.Content>
                  {#each PAYMENT_TERMS as term}
                    <Select.Item value={term.value}>{term.label}</Select.Item>
                  {/each}
                </Select.Content>
              </Select.Root>
            </div>
          </div>
        </div>
      </div>

      <!-- From / To Section -->
      <div class="grid grid-cols-2 gap-8 border-b p-6">
        <!-- Bill From (Account) -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 font-medium">
            <Building2 class="text-muted-foreground size-4" />
            <span>Cobrado De (Conta)</span>
            <span class="text-destructive">*</span>
          </div>
          <Select.Root type="single" value={invoice.accountId} onValueChange={handleAccountChange}>
            <Select.Trigger class="w-full">
              {accounts.find((a) => a.id === invoice.accountId)?.name || 'Selecionar Conta'}
            </Select.Trigger>
            <Select.Content>
              {#each accounts as account}
                <Select.Item value={account.id}>{account.name}</Select.Item>
              {/each}
            </Select.Content>
          </Select.Root>
          {#if invoice.accountId}
            <div class="bg-muted/50 rounded-md p-3 text-sm">
              <p class="font-medium">{invoice.clientName || 'Nome da Conta'}</p>
              <!-- Account address would go here if available -->
            </div>
          {/if}
        </div>

        <!-- Bill To (Contact) -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 font-medium">
            <User class="text-muted-foreground size-4" />
            <span>Cobrado Para (Contato)</span>
            <span class="text-destructive">*</span>
          </div>
          <Select.Root type="single" value={invoice.contactId} onValueChange={handleContactChange}>
            <Select.Trigger class="w-full">
              {contacts.find((c) => c.id === invoice.contactId)?.name || 'Selecionar Contato'}
            </Select.Trigger>
            <Select.Content>
              {#each filteredContacts as contact}
                <Select.Item value={contact.id}>{contact.name}</Select.Item>
              {/each}
            </Select.Content>
          </Select.Root>
          {#if invoice.contactId}
            <div class="space-y-2">
              <Input bind:value={invoice.clientName} placeholder="Nome do Cliente" />
              <Input bind:value={invoice.clientEmail} placeholder="Email" type="email" />
              <Input bind:value={invoice.clientPhone} placeholder="Telefone" />
              <Input bind:value={invoice.clientAddressLine} placeholder="Endereço" />
              <div class="grid grid-cols-2 gap-2">
                <Input bind:value={invoice.clientCity} placeholder="Cidade" />
                <Input bind:value={invoice.clientState} placeholder="Estado" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <Input bind:value={invoice.clientPostcode} placeholder="Código Postal" />
                <Select.Root
                  type="single"
                  value={invoice.clientCountry}
                  onValueChange={(v) => { invoice.clientCountry = v; countrySearch = ''; }}
                  onOpenChange={(open) => { if (!open) countrySearch = ''; }}
                >
                  <Select.Trigger class="w-full">
                    {COUNTRIES.find((c) => c.code === invoice.clientCountry)?.name || 'País'}
                  </Select.Trigger>
                  <Select.Content class="max-h-60">
                    <div class="sticky top-0 bg-[var(--surface-raised)] p-2">
                      <Input
                        type="text"
                        placeholder="Buscar país..."
                        bind:value={countrySearch}
                        class="h-8 text-sm"
                        onclick={(e) => e.stopPropagation()}
                        onkeydown={(e) => e.stopPropagation()}
                      />
                    </div>
                    {#each filteredCountryOptions as country}
                      <Select.Item value={country.code}>{country.name}</Select.Item>
                    {/each}
                    {#if filteredCountryOptions.length === 0}
                      <div class="px-3 py-2 text-sm text-gray-500">Nenhum país encontrado</div>
                    {/if}
                  </Select.Content>
                </Select.Root>
              </div>
            </div>
          {/if}
        </div>
      </div>

      <!-- Line Items -->
      <div class="p-6">
        <h3 class="mb-4 font-medium">Itens</h3>
        <div class="rounded-md border">
          <!-- Table Header -->
          <div
            class="bg-muted/50 text-muted-foreground grid grid-cols-12 gap-4 border-b px-4 py-3 text-sm font-medium"
          >
            <div class="col-span-5">Descrição</div>
            <div class="col-span-2 text-right">Qtd</div>
            <div class="col-span-2 text-right">Valor</div>
            <div class="col-span-2 text-right">Valor Total</div>
            <div class="col-span-1"></div>
          </div>

          <!-- Line Items -->
          {#each lineItems as item, index (item.id)}
            <div class="grid grid-cols-12 items-start gap-4 border-b px-4 py-3 last:border-b-0">
              <div class="col-span-5 space-y-2">
                <Input
                  bind:value={item.name}
                  placeholder="Nome do item"
                  class="border-0 bg-transparent px-0 font-medium focus-visible:ring-0"
                />
                <Input
                  bind:value={item.description}
                  placeholder="Descrição adicional (opcional)"
                  class="text-muted-foreground border-0 bg-transparent px-0 text-xs focus-visible:ring-0"
                />
              </div>
              <div class="col-span-2">
                <Input
                  type="number"
                  bind:value={item.quantity}
                  min="0"
                  step="1"
                  class="border-0 bg-transparent px-0 text-right focus-visible:ring-0"
                  oninput={() => updateLineItemAmount(index)}
                />
              </div>
              <div class="col-span-2">
                <Input
                  type="number"
                  bind:value={item.rate}
                  min="0"
                  step="0.01"
                  class="border-0 bg-transparent px-0 text-right focus-visible:ring-0"
                  oninput={() => updateLineItemAmount(index)}
                />
              </div>
              <div class="col-span-2 text-right font-medium">
                {formatCurrency(item.quantity * item.rate, invoice.currency)}
              </div>
              <div class="col-span-1 text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  class="text-muted-foreground hover:text-destructive size-8"
                  onclick={() => removeLineItem(index)}
                  disabled={lineItems.length === 1}
                >
                  <Trash2 class="size-4" />
                </Button>
              </div>
            </div>
          {/each}

          <!-- Add Line Button -->
          <div class="px-4 py-3">
            <Button variant="ghost" size="sm" onclick={addLineItem} class="text-primary">
              <Plus class="mr-2 size-4" />
              Adicionar Item
            </Button>
          </div>
        </div>
      </div>

      <!-- Totals -->
      <div class="flex justify-end border-t p-6">
        <div class="w-80 space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-muted-foreground">Subtotal</span>
            <span class="font-medium">{formatCurrency(subtotal, invoice.currency)}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">Imposto</span>
              <Input
                type="number"
                bind:value={taxRate}
                min="0"
                max="100"
                step="0.1"
                class="h-7 w-16 text-right text-xs"
              />
              <span class="text-muted-foreground">%</span>
            </div>
            <span class="font-medium">{formatCurrency(taxAmount, invoice.currency)}</span>
          </div>
          <Separator />
          <div class="flex justify-between text-lg font-semibold">
            <span>Total</span>
            <span class="text-primary">{formatCurrency(total, invoice.currency)}</span>
          </div>
        </div>
      </div>

      <!-- Notes & Terms -->
      <div class="grid grid-cols-2 gap-8 border-t p-6">
        <div class="space-y-2">
          <Label class="text-sm font-medium">Notas</Label>
          <Textarea
            bind:value={invoice.notes}
            placeholder="Notas visíveis ao cliente na fatura..."
            rows={4}
          />
        </div>
        <div class="space-y-2">
          <Label class="text-sm font-medium">Termos e Condições</Label>
          <Textarea
            bind:value={invoice.terms}
            placeholder="Termos de pagamento, multas por atraso, etc..."
            rows={4}
          />
        </div>
      </div>
    </div>
  </div>
</div>
