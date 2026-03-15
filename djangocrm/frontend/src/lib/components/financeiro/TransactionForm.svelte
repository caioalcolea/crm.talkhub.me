<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { SearchableSelect } from '$lib/components/ui/searchable-select/index.js';

  let {
    formData = $bindable({}),
    formOptions = {},
    mode = 'create',
    canEditFinancials = true,
    onsubmit,
    oncancel,
    loading = false
  } = $props();

  const tipoOptions = [
    { value: 'PAGAR', label: 'Conta a Pagar' },
    { value: 'RECEBER', label: 'Conta a Receber' }
  ];

  const recorrenciaOptions = [
    { value: 'MENSAL', label: 'Mensal' },
    { value: 'QUINZENAL', label: 'Quinzenal' },
    { value: 'SEMANAL', label: 'Semanal' },
    { value: 'ANUAL', label: 'Anual' }
  ];

  let orgCurrency = $derived(formOptions.org_currency || 'BRL');
  let isSameCurrency = $derived(formData.currency === orgCurrency);
  let showFinancials = $derived(mode === 'create' || (mode === 'edit' && canEditFinancials));

  // Build grouped planos for SearchableSelect
  let planoGroups = $derived.by(() => {
    const planos = formOptions.planos || [];
    const grupos = formOptions.plano_grupos || [];
    if (grupos.length === 0) {
      // Fallback: flat list
      return [];
    }
    const grupoMap = new Map();
    for (const g of grupos) {
      grupoMap.set(g.id, { label: `${g.codigo} - ${g.nome}`, options: [] });
    }
    for (const p of planos) {
      const group = grupoMap.get(p.grupo_id);
      if (group) {
        group.options.push({ value: p.id, label: p.nome });
      }
    }
    return [...grupoMap.values()].filter((g) => g.options.length > 0);
  });

  // Flat fallback for planos (when no groups available)
  let planoOptions = $derived.by(() => {
    if (planoGroups.length > 0) return [];
    return (formOptions.planos || []).map((p) => ({ value: p.id, label: p.nome }));
  });

  // Flat options for other selects
  let accountOptions = $derived(
    (formOptions.accounts || []).map((a) => ({ value: a.id, label: a.name }))
  );
  let contactOptions = $derived(
    (formOptions.contacts || []).map((c) => ({ value: c.id, label: c.name }))
  );
  let formaOptions = $derived(
    (formOptions.formas_pagamento || []).map((f) => ({ value: f.id, label: f.nome }))
  );
  let currencyOptions = $derived(
    (formOptions.currencies || []).map((c) => ({ value: c.code, label: `${c.code} - ${c.symbol}` }))
  );

  // Auto-set exchange rate to 1 when same currency
  $effect(() => {
    if (isSameCurrency) {
      formData.exchange_rate_to_base = '1';
      if (formData.exchange_rate_type === 'VARIAVEL') {
        formData.exchange_rate_type = 'FIXO';
      }
    }
  });

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
    <label for="descricao" class="text-sm font-medium">Descricao *</label>
    <input
      id="descricao"
      type="text"
      bind:value={formData.descricao}
      class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
      placeholder="Descricao do lancamento"
      required
    />
  </div>

  <!-- Centro de Custo (grouped by plano grupo) -->
  <div>
    <label class="text-sm font-medium">Centro de Custo</label>
    <div class="mt-1">
      <SearchableSelect
        bind:value={formData.plano_de_contas}
        groups={planoGroups}
        options={planoOptions}
        placeholder="Selecione o centro de custo..."
        searchPlaceholder="Buscar centro de custo..."
        emptyText="Nenhum centro de custo encontrado."
      />
    </div>
  </div>

  <!-- Account / Contact -->
  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
    <div>
      <label class="text-sm font-medium">Empresa</label>
      <div class="mt-1">
        <SearchableSelect
          bind:value={formData.account}
          options={accountOptions}
          placeholder="Selecione a empresa..."
          searchPlaceholder="Buscar empresa..."
          emptyText="Nenhuma empresa encontrada."
        />
      </div>
    </div>
    <div>
      <label class="text-sm font-medium">Contato</label>
      <div class="mt-1">
        <SearchableSelect
          bind:value={formData.contact}
          options={contactOptions}
          placeholder="Selecione o contato..."
          searchPlaceholder="Buscar contato..."
          emptyText="Nenhum contato encontrado."
        />
      </div>
    </div>
  </div>

  <!-- Currency + Value + Exchange Rate (only for create or full-edit) -->
  {#if showFinancials}
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div>
        <label class="text-sm font-medium">Moeda</label>
        <div class="mt-1">
          <SearchableSelect
            bind:value={formData.currency}
            options={currencyOptions}
            placeholder="Moeda..."
            searchPlaceholder="Buscar moeda..."
            allowClear={false}
          />
        </div>
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
      {#if !isSameCurrency}
        <div>
          <label for="exchange_rate_type" class="text-sm font-medium">Tipo de Taxa</label>
          <select
            id="exchange_rate_type"
            bind:value={formData.exchange_rate_type}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
          >
            <option value="FIXO">Fixa (manual)</option>
            <option value="VARIAVEL">Variavel (automatica)</option>
          </select>
        </div>
      {/if}
    </div>

    <!-- Exchange rate input (only for FIXO and different currency) -->
    {#if !isSameCurrency && formData.exchange_rate_type !== 'VARIAVEL'}
      <div class="max-w-[200px]">
        <label for="exchange_rate_to_base" class="text-sm font-medium">
          Taxa de Cambio (1 {formData.currency} = X {orgCurrency})
        </label>
        <input
          id="exchange_rate_to_base"
          type="number"
          step="0.00000001"
          min="0"
          bind:value={formData.exchange_rate_to_base}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
        />
      </div>
    {:else if !isSameCurrency && formData.exchange_rate_type === 'VARIAVEL'}
      <p class="text-muted-foreground rounded-md border border-dashed px-3 py-2 text-xs">
        A taxa de cambio sera buscada automaticamente na data do lancamento.
      </p>
    {/if}

    <!-- Parcelas + Vencimento + Forma -->
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div>
        <label for="numero_parcelas" class="text-sm font-medium">Parcelas</label>
        <input
          id="numero_parcelas"
          type="number"
          min="1"
          max="120"
          bind:value={formData.numero_parcelas}
          disabled={formData.is_recorrente}
          class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none disabled:opacity-50"
        />
        {#if formData.is_recorrente}
          <p class="text-muted-foreground mt-0.5 text-[10px]">Automatico (recorrente)</p>
        {/if}
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
        <label class="text-sm font-medium">Forma de Pgto</label>
        <div class="mt-1">
          <SearchableSelect
            bind:value={formData.forma_pagamento}
            options={formaOptions}
            placeholder="Selecione..."
            searchPlaceholder="Buscar forma..."
            emptyText="Nenhuma forma encontrada."
          />
        </div>
      </div>
    </div>

    <!-- Recurring toggle -->
    <div class="rounded-md border p-3 space-y-3">
      <label class="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          bind:checked={formData.is_recorrente}
          class="h-4 w-4 rounded border-gray-300"
        />
        <span class="font-medium">Lancamento recorrente</span>
      </label>

      {#if formData.is_recorrente}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="recorrencia_tipo" class="text-sm font-medium">Frequencia *</label>
            <select
              id="recorrencia_tipo"
              bind:value={formData.recorrencia_tipo}
              class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
              required
            >
              <option value="">Selecione...</option>
              {#each recorrenciaOptions as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="data_fim_recorrencia" class="text-sm font-medium">Data Fim (opcional)</label>
            <input
              id="data_fim_recorrencia"
              type="date"
              bind:value={formData.data_fim_recorrencia}
              class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
            />
            <p class="text-muted-foreground mt-0.5 text-[10px]">Deixe vazio para recorrencia sem fim</p>
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Observacoes -->
  <div>
    <label for="observacoes" class="text-sm font-medium">Observacoes</label>
    <textarea
      id="observacoes"
      bind:value={formData.observacoes}
      rows="3"
      class="border-input bg-background mt-1 flex w-full rounded-md border px-3 py-2 text-sm focus-visible:outline-none"
      placeholder="Observacoes adicionais..."
    ></textarea>
  </div>

  <!-- Actions -->
  <div class="flex justify-end gap-2 pt-2">
    <Button variant="outline" type="button" onclick={oncancel}>Cancelar</Button>
    <Button type="submit" disabled={loading}>
      {loading ? 'Salvando...' : mode === 'create' ? 'Criar Lancamento' : 'Salvar'}
    </Button>
  </div>
</form>
