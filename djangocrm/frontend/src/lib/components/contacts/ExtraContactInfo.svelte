<script>
  import { toast } from 'svelte-sonner';
  import { Plus, X, Mail, Phone, MapPin } from '@lucide/svelte';
  import { apiRequest } from '$lib/api.js';
  import { Button } from '$lib/components/ui/button/index.js';

  /** @type {{ contactId: string, extraEmails?: any[], extraPhones?: any[], extraAddresses?: any[] }} */
  let {
    contactId,
    extraEmails = $bindable([]),
    extraPhones = $bindable([]),
    extraAddresses = $bindable([])
  } = $props();

  // New entry forms
  let showNewEmail = $state(false);
  let showNewPhone = $state(false);
  let showNewAddress = $state(false);

  let newEmail = $state({ email: '', label: 'work' });
  let newPhone = $state({ phone: '', label: 'mobile' });
  let newAddress = $state({
    label: 'work',
    addressLine: '',
    city: '',
    state: '',
    postcode: '',
    country: ''
  });

  let saving = $state(false);

  const emailLabels = [
    { value: 'work', label: 'Trabalho' },
    { value: 'personal', label: 'Pessoal' },
    { value: 'other', label: 'Outro' }
  ];

  const phoneLabels = [
    { value: 'work', label: 'Trabalho' },
    { value: 'personal', label: 'Pessoal' },
    { value: 'mobile', label: 'Celular' },
    { value: 'whatsapp', label: 'WhatsApp' },
    { value: 'other', label: 'Outro' }
  ];

  const addressLabels = [
    { value: 'work', label: 'Trabalho' },
    { value: 'home', label: 'Residência' },
    { value: 'billing', label: 'Cobrança' },
    { value: 'shipping', label: 'Entrega' },
    { value: 'other', label: 'Outro' }
  ];

  /**
   * @param {string} labelValue
   * @param {{ value: string, label: string }[]} labels
   */
  function getLabelText(labelValue, labels) {
    return labels.find((l) => l.value === labelValue)?.label || labelValue;
  }

  async function addEmail() {
    if (!newEmail.email.trim()) return;
    saving = true;
    try {
      const result = await apiRequest(`/contacts/${contactId}/emails/`, {
        method: 'POST',
        body: { email: newEmail.email.trim(), label: newEmail.label }
      });
      extraEmails = [...extraEmails, { id: result.id, email: result.email, label: result.label }];
      newEmail = { email: '', label: 'work' };
      showNewEmail = false;
      toast.success('E-mail adicionado');
    } catch (err) {
      toast.error(err.message || 'Erro ao adicionar e-mail');
    } finally {
      saving = false;
    }
  }

  /** @param {string} id */
  async function removeEmail(id) {
    try {
      await apiRequest(`/contacts/${contactId}/emails/${id}/`, { method: 'DELETE' });
      extraEmails = extraEmails.filter((e) => e.id !== id);
      toast.success('E-mail removido');
    } catch (err) {
      toast.error(err.message || 'Erro ao remover e-mail');
    }
  }

  async function addPhone() {
    if (!newPhone.phone.trim()) return;
    saving = true;
    try {
      const result = await apiRequest(`/contacts/${contactId}/phones/`, {
        method: 'POST',
        body: { phone: newPhone.phone.trim(), label: newPhone.label }
      });
      extraPhones = [...extraPhones, { id: result.id, phone: result.phone, label: result.label }];
      newPhone = { phone: '', label: 'mobile' };
      showNewPhone = false;
      toast.success('Telefone adicionado');
    } catch (err) {
      toast.error(err.message || 'Erro ao adicionar telefone');
    } finally {
      saving = false;
    }
  }

  /** @param {string} id */
  async function removePhone(id) {
    try {
      await apiRequest(`/contacts/${contactId}/phones/${id}/`, { method: 'DELETE' });
      extraPhones = extraPhones.filter((p) => p.id !== id);
      toast.success('Telefone removido');
    } catch (err) {
      toast.error(err.message || 'Erro ao remover telefone');
    }
  }

  async function addAddress() {
    if (!newAddress.addressLine.trim()) return;
    saving = true;
    try {
      const result = await apiRequest(`/contacts/${contactId}/addresses/`, {
        method: 'POST',
        body: {
          label: newAddress.label,
          address_line: newAddress.addressLine.trim(),
          city: newAddress.city.trim(),
          state: newAddress.state.trim(),
          postcode: newAddress.postcode.trim(),
          country: newAddress.country.trim()
        }
      });
      extraAddresses = [
        ...extraAddresses,
        {
          id: result.id,
          label: result.label,
          addressLine: result.address_line,
          city: result.city,
          state: result.state,
          postcode: result.postcode,
          country: result.country
        }
      ];
      newAddress = { label: 'work', addressLine: '', city: '', state: '', postcode: '', country: '' };
      showNewAddress = false;
      toast.success('Endereço adicionado');
    } catch (err) {
      toast.error(err.message || 'Erro ao adicionar endereço');
    } finally {
      saving = false;
    }
  }

  /** @param {string} id */
  async function removeAddress(id) {
    try {
      await apiRequest(`/contacts/${contactId}/addresses/${id}/`, { method: 'DELETE' });
      extraAddresses = extraAddresses.filter((a) => a.id !== id);
      toast.success('Endereço removido');
    } catch (err) {
      toast.error(err.message || 'Erro ao remover endereço');
    }
  }
</script>

<div class="space-y-4">
  <!-- Extra Emails -->
  <div>
    <div class="mb-1.5 flex items-center justify-between">
      <p class="flex items-center gap-1.5 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
        <Mail class="size-3.5" />
        E-mails Adicionais
      </p>
      <button
        type="button"
        class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text-primary)]"
        onclick={() => (showNewEmail = !showNewEmail)}
      >
        <Plus class="size-3" />
        Adicionar
      </button>
    </div>

    {#if extraEmails.length > 0}
      <div class="space-y-1">
        {#each extraEmails as entry (entry.id)}
          <div
            class="flex items-center justify-between rounded-md border border-[var(--border-default)] px-2.5 py-1.5 text-sm"
          >
            <div class="flex items-center gap-2">
              <span class="text-[var(--text-primary)]">{entry.email}</span>
              <span
                class="rounded bg-[var(--surface-sunken)] px-1.5 py-0.5 text-xs text-[var(--text-tertiary)]"
              >
                {getLabelText(entry.label, emailLabels)}
              </span>
            </div>
            <button
              type="button"
              class="text-[var(--text-tertiary)] transition-colors hover:text-red-500"
              onclick={() => removeEmail(entry.id)}
            >
              <X class="size-3.5" />
            </button>
          </div>
        {/each}
      </div>
    {/if}

    {#if showNewEmail}
      <div class="flex items-end gap-2 rounded-md border border-dashed border-[var(--border-default)] p-2">
        <div class="flex-1">
          <input
            type="email"
            placeholder="email@exemplo.com"
            class="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
            bind:value={newEmail.email}
            onkeydown={(e) => e.key === 'Enter' && addEmail()}
          />
        </div>
        <select
          class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
          bind:value={newEmail.label}
        >
          {#each emailLabels as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
        <Button size="sm" onclick={addEmail} disabled={saving || !newEmail.email.trim()}>
          {saving ? '...' : 'Salvar'}
        </Button>
      </div>
    {/if}
  </div>

  <!-- Extra Phones -->
  <div>
    <div class="mb-1.5 flex items-center justify-between">
      <p class="flex items-center gap-1.5 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
        <Phone class="size-3.5" />
        Telefones Adicionais
      </p>
      <button
        type="button"
        class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text-primary)]"
        onclick={() => (showNewPhone = !showNewPhone)}
      >
        <Plus class="size-3" />
        Adicionar
      </button>
    </div>

    {#if extraPhones.length > 0}
      <div class="space-y-1">
        {#each extraPhones as entry (entry.id)}
          <div
            class="flex items-center justify-between rounded-md border border-[var(--border-default)] px-2.5 py-1.5 text-sm"
          >
            <div class="flex items-center gap-2">
              <span class="text-[var(--text-primary)]">{entry.phone}</span>
              <span
                class="rounded bg-[var(--surface-sunken)] px-1.5 py-0.5 text-xs text-[var(--text-tertiary)]"
              >
                {getLabelText(entry.label, phoneLabels)}
              </span>
            </div>
            <button
              type="button"
              class="text-[var(--text-tertiary)] transition-colors hover:text-red-500"
              onclick={() => removePhone(entry.id)}
            >
              <X class="size-3.5" />
            </button>
          </div>
        {/each}
      </div>
    {/if}

    {#if showNewPhone}
      <div class="flex items-end gap-2 rounded-md border border-dashed border-[var(--border-default)] p-2">
        <div class="flex-1">
          <input
            type="tel"
            placeholder="+55 (11) 0000-0000"
            class="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
            bind:value={newPhone.phone}
            onkeydown={(e) => e.key === 'Enter' && addPhone()}
          />
        </div>
        <select
          class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
          bind:value={newPhone.label}
        >
          {#each phoneLabels as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
        <Button size="sm" onclick={addPhone} disabled={saving || !newPhone.phone.trim()}>
          {saving ? '...' : 'Salvar'}
        </Button>
      </div>
    {/if}
  </div>

  <!-- Extra Addresses -->
  <div>
    <div class="mb-1.5 flex items-center justify-between">
      <p class="flex items-center gap-1.5 text-xs font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
        <MapPin class="size-3.5" />
        Endereços Adicionais
      </p>
      <button
        type="button"
        class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text-primary)]"
        onclick={() => (showNewAddress = !showNewAddress)}
      >
        <Plus class="size-3" />
        Adicionar
      </button>
    </div>

    {#if extraAddresses.length > 0}
      <div class="space-y-1">
        {#each extraAddresses as entry (entry.id)}
          <div
            class="flex items-start justify-between rounded-md border border-[var(--border-default)] px-2.5 py-1.5 text-sm"
          >
            <div>
              <div class="flex items-center gap-2">
                <span class="text-[var(--text-primary)]">{entry.addressLine}</span>
                <span
                  class="rounded bg-[var(--surface-sunken)] px-1.5 py-0.5 text-xs text-[var(--text-tertiary)]"
                >
                  {getLabelText(entry.label, addressLabels)}
                </span>
              </div>
              {#if entry.city || entry.state || entry.postcode}
                <p class="mt-0.5 text-xs text-[var(--text-secondary)]">
                  {[entry.city, entry.state, entry.postcode].filter(Boolean).join(', ')}
                </p>
              {/if}
            </div>
            <button
              type="button"
              class="mt-0.5 text-[var(--text-tertiary)] transition-colors hover:text-red-500"
              onclick={() => removeAddress(entry.id)}
            >
              <X class="size-3.5" />
            </button>
          </div>
        {/each}
      </div>
    {/if}

    {#if showNewAddress}
      <div class="space-y-2 rounded-md border border-dashed border-[var(--border-default)] p-2">
        <div class="flex gap-2">
          <select
            class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
            bind:value={newAddress.label}
          >
            {#each addressLabels as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>
        <input
          type="text"
          placeholder="Endereço"
          class="w-full rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
          bind:value={newAddress.addressLine}
        />
        <div class="grid grid-cols-2 gap-2">
          <input
            type="text"
            placeholder="Cidade"
            class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
            bind:value={newAddress.city}
          />
          <input
            type="text"
            placeholder="Estado"
            class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
            bind:value={newAddress.state}
          />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <input
            type="text"
            placeholder="CEP"
            class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
            bind:value={newAddress.postcode}
          />
          <input
            type="text"
            placeholder="País"
            class="rounded-md border border-[var(--border-default)] bg-[var(--surface-default)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--color-primary-default)]"
            bind:value={newAddress.country}
          />
        </div>
        <div class="flex justify-end">
          <Button
            size="sm"
            onclick={addAddress}
            disabled={saving || !newAddress.addressLine.trim()}
          >
            {saving ? '...' : 'Salvar'}
          </Button>
        </div>
      </div>
    {/if}
  </div>
</div>
