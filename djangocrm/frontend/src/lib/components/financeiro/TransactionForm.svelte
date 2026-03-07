<script>
  import { Button } from '$lib/components/ui/button/index.js';

  let {
    formData = $bindable({}),
    formOptions = {},
    mode = 'create',
    onsubmit,
    oncancel,
    loading = false
  } = $props();

  const tipoOptions = [
    { value: 'PAGAR', label: 'Conta a Pagar' },
    { value: 'RECEBER', label: 'Conta a Receber' }
  ];

  function handleSubmit(e) {
    e.preventDefault();
    onsubmit?.(formData);
  }
</script>

<form onsubmit={handleSubmit} class="space-y-4">
  <!-- Tipo -->
  {#if mode === 'create'}
    <div>
      <label for="tipo" class="text-sm font-medium">Tipo *</label>
      <select
        id="tipo"
        bind:value={formData.tipo}
        class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
        required
      >
        <option value="">Selecione...</option>
        {#each tipoOptions as opt}
          <option value={opt.value}>{opt.label}</option>
        {/each}
      </select>
    </div>
  {/if}

  <!-- Descricao -->
  <div>
    <label for="descricao" class="text-sm font-medium">Descrição *</label>
    <input
      id="descricao"
      type="text"
      bind:value={formData.descricao}
      class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
      placeholder="Descrição do lançamento"
      required
    />
  </div>

  <!-- Centro de Custo -->
  <div>
    <label for="plano_de_contas" class="text-sm font-medium">Centro de Custo</label>
    <select
      id="plano_de_contas"
      bind:value={formData.plano_de_contas}
      class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
    >
      <option value="">Nenhum</option>
      {#each formOptions.planos || [] as plano}
        <option value={plano.id}>{plano.nome}</option>
      {/each}
    </select>
  </div>

  <!-- Account / Contact -->
  <div class="grid grid-cols-2 gap-3">
    <div>
      <label for="account" class="text-sm font-medium">Empresa</label>
      <select
        id="account"
        bind:value={formData.account}
        class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
      >
        <option value="">Nenhuma</option>
        {#each formOptions.accounts || [] as acc}
          <option value={acc.id}>{acc.name}</option>
        {/each}
      </select>
    </div>
    <div>
      <label for="contact" class="text-sm font-medium">Contato</label>
      <select
        id="contact"
        bind:value={formData.contact}
        class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
      >
        <option value="">Nenhum</option>
        {#each formOptions.contacts || [] as ct}
          <option value={ct.id}>{ct.name}</option>
        {/each}
      </select>
    </div>
  </div>

  <!-- Currency + Value + Exchange Rate -->
  {#if mode === 'create'}
    <div class="grid grid-cols-3 gap-3">
      <div>
        <label for="currency" class="text-sm font-medium">Moeda</label>
        <select
          id="currency"
          bind:value={formData.currency}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
        >
          {#each formOptions.currencies || [] as curr}
            <option value={curr.code}>{curr.code} - {curr.symbol}</option>
          {/each}
        </select>
      </div>
      <div>
        <label for="valor_total" class="text-sm font-medium">Valor Total *</label>
        <input
          id="valor_total"
          type="number"
          step="0.00000001"
          min="0.01"
          bind:value={formData.valor_total}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
          required
        />
      </div>
      <div>
        <label for="exchange_rate_to_base" class="text-sm font-medium">Taxa de Câmbio</label>
        <input
          id="exchange_rate_to_base"
          type="number"
          step="0.00000001"
          min="0"
          bind:value={formData.exchange_rate_to_base}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
        />
      </div>
    </div>

    <!-- Parcelas + Vencimento + Forma -->
    <div class="grid grid-cols-3 gap-3">
      <div>
        <label for="numero_parcelas" class="text-sm font-medium">Parcelas</label>
        <input
          id="numero_parcelas"
          type="number"
          min="1"
          max="120"
          bind:value={formData.numero_parcelas}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
        />
      </div>
      <div>
        <label for="data_primeiro_vencimento" class="text-sm font-medium">1° Vencimento *</label>
        <input
          id="data_primeiro_vencimento"
          type="date"
          bind:value={formData.data_primeiro_vencimento}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
          required
        />
      </div>
      <div>
        <label for="forma_pagamento" class="text-sm font-medium">Forma de Pgto</label>
        <select
          id="forma_pagamento"
          bind:value={formData.forma_pagamento}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
        >
          <option value="">Nenhuma</option>
          {#each formOptions.formas_pagamento || [] as forma}
            <option value={forma.id}>{forma.nome}</option>
          {/each}
        </select>
      </div>
    </div>
  {/if}

  <!-- Observacoes -->
  <div>
    <label for="observacoes" class="text-sm font-medium">Observações</label>
    <textarea
      id="observacoes"
      bind:value={formData.observacoes}
      rows="3"
      class="border-input bg-background mt-1 flex w-full rounded-md border px-3 py-2 text-sm focus-visible:outline-none"
      placeholder="Observações adicionais..."
    ></textarea>
  </div>

  <!-- Actions -->
  <div class="flex justify-end gap-2 pt-2">
    <Button variant="outline" type="button" onclick={oncancel}>Cancelar</Button>
    <Button type="submit" disabled={loading}>
      {loading ? 'Salvando...' : mode === 'create' ? 'Criar Lançamento' : 'Salvar'}
    </Button>
  </div>
</form>
