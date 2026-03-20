<script>
  import { Button } from '$lib/components/ui/button/index.js';
  import { SearchableSelect } from '$lib/components/ui/searchable-select/index.js';
  import { Bell, ChevronDown, ChevronRight, Zap } from '@lucide/svelte';
  import AICopilot from '$lib/components/autopilot/AICopilot.svelte';

  let {
    formData = $bindable({}),
    formOptions = {},
    mode = 'create',
    canEditFinancials = true,
    onsubmit,
    oncancel,
    loading = false,
    reminderConfig = $bindable(null),
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

  // Parcela preview: show user how the value will be split
  let parcelaPreview = $derived.by(() => {
    const total = parseFloat(formData.valor_total) || 0;
    const n = parseInt(formData.numero_parcelas) || 1;
    if (total <= 0 || n < 1) return null;
    if (formData.is_recorrente) {
      return { mode: 'recurring', valorEach: total, count: n, totalEffective: total * n };
    }
    if (n === 1) return null;
    const valorEach = Math.round((total / n) * 100) / 100;
    return { mode: 'installment', valorEach, count: n, totalEffective: total };
  });

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
  let productOptions = $derived(
    (formOptions.products || []).map((p) => ({
      value: p.id,
      label: `${p.name}${p.product_type === 'service' ? ' (Serviço)' : ''}${p.track_inventory ? ` [${p.stock_quantity}]` : ''}`
    }))
  );

  // Auto-fill fields when product is selected
  let _lastProductId = '';
  $effect(() => {
    const productId = formData.product;
    if (!productId || productId === _lastProductId) return;
    _lastProductId = productId;
    const prod = (formOptions.products || []).find((p) => p.id === productId);
    if (!prod) return;
    // Auto-fill valor_total only if empty
    if (!formData.valor_total || formData.valor_total === '') {
      const qty = parseFloat(formData.quantity) || 1;
      formData.valor_total = (parseFloat(prod.price) * qty).toFixed(2);
    }
    // Auto-fill currency if product has one
    if (prod.currency && formData.currency === orgCurrency) {
      formData.currency = prod.currency;
    }
    // Auto-fill plano de contas
    if (!formData.plano_de_contas) {
      if (formData.tipo === 'RECEBER' && prod.default_plano_receita) {
        formData.plano_de_contas = prod.default_plano_receita;
      } else if (formData.tipo === 'PAGAR' && prod.default_plano_custo) {
        formData.plano_de_contas = prod.default_plano_custo;
      }
    }
  });

  // Auto-set exchange rate to 1 when same currency
  $effect(() => {
    if (isSameCurrency) {
      formData.exchange_rate_to_base = '1';
      if (formData.exchange_rate_type === 'VARIAVEL') {
        formData.exchange_rate_type = 'FIXO';
      }
    }
  });

  // ── Inline Reminder Config ──────────────────────────────
  let enableReminder = $state(false);
  let reminderExpanded = $state(false);

  let reminderForm = $state({
    name: '',
    trigger_type: 'due_date',
    trigger_config: { date_field: 'data_vencimento', offsets: [-7, -3, 0, 1, 3] },
    channel_config: { channel_type: 'internal', destination_type: 'owner_email' },
    task_config: { enabled: true, mode: 'per_run', title_template: '', priority: 'High' },
    message_template: '',
    approval_policy: 'auto',
  });

  const QUICK_PRESETS = [
    {
      label: 'Padrão (7/3/0/+1/+3 dias)',
      config: {
        name: 'Lembrete padrão',
        trigger_type: 'due_date',
        trigger_config: { date_field: 'data_vencimento', offsets: [-7, -3, 0, 1, 3] },
        channel_config: { channel_type: 'internal', destination_type: 'owner_email' },
        task_config: { enabled: true, mode: 'per_run', title_template: 'Cobrança: {{contact_name}} - {{amount}} {{currency}}', priority: 'High' },
        message_template: 'Lembrete: {{contact_name}} — {{amount}} {{currency}} vence em {{due_date}}.',
        approval_policy: 'auto',
      }
    },
    {
      label: 'Recorrente (3 em 3 dias)',
      config: {
        name: 'Cobrança recorrente',
        trigger_type: 'recurring',
        trigger_config: { interval_days: 3, max_runs: 10, start_after: 'data_vencimento' },
        channel_config: { channel_type: 'internal', destination_type: 'owner_email' },
        task_config: { enabled: true, mode: 'per_run', title_template: 'Cobrança pendente: {{contact_name}}', priority: 'High' },
        message_template: 'Cobrança pendente: {{contact_name}} — {{amount}} {{currency}} em atraso {{days_overdue}} dias.',
        approval_policy: 'auto',
      }
    },
    {
      label: 'Email ao contato',
      config: {
        name: 'Lembrete por email',
        trigger_type: 'due_date',
        trigger_config: { date_field: 'data_vencimento', offsets: [-5, 0, 2] },
        channel_config: { channel_type: 'smtp_native', destination_type: 'contact_email' },
        task_config: { enabled: false },
        message_template: 'Olá {{contact_name}}, este é um lembrete sobre o valor de {{amount}} {{currency}} com vencimento em {{due_date}}.',
        approval_policy: 'manual',
      }
    },
  ];

  const OFFSET_PRESETS = [
    { label: '7d antes', value: -7 },
    { label: '5d antes', value: -5 },
    { label: '3d antes', value: -3 },
    { label: '1d antes', value: -1 },
    { label: 'No dia', value: 0 },
    { label: '1d após', value: 1 },
    { label: '3d após', value: 3 },
    { label: '7d após', value: 7 },
  ];

  const CHANNEL_OPTIONS = [
    { value: 'internal', label: 'Notificação interna' },
    { value: 'smtp_native', label: 'Email (SMTP)' },
  ];

  const TRIGGER_OPTIONS = [
    { value: 'due_date', label: 'Por data de vencimento' },
    { value: 'recurring', label: 'Recorrente após vencimento' },
  ];

  function applyQuickPreset(preset) {
    reminderForm = { ...preset.config };
    reminderExpanded = true;
  }

  function toggleOffset(val) {
    const offsets = reminderForm.trigger_config.offsets || [];
    const idx = offsets.indexOf(val);
    if (idx >= 0) {
      reminderForm.trigger_config = {
        ...reminderForm.trigger_config,
        offsets: offsets.filter((_, i) => i !== idx),
      };
    } else {
      reminderForm.trigger_config = {
        ...reminderForm.trigger_config,
        offsets: [...offsets, val].sort((a, b) => a - b),
      };
    }
  }

  function handleAIReminder(result) {
    if (result.name) reminderForm.name = result.name;
    if (result.trigger_type) reminderForm.trigger_type = result.trigger_type;
    if (result.trigger_config) reminderForm.trigger_config = result.trigger_config;
    if (result.channel_config) reminderForm.channel_config = result.channel_config;
    if (result.task_config) reminderForm.task_config = result.task_config;
    if (result.message_template) reminderForm.message_template = result.message_template;
    if (result.approval_policy) reminderForm.approval_policy = result.approval_policy;
    reminderExpanded = true;
  }

  // Sync reminderConfig bindable with parent
  $effect(() => {
    if (enableReminder) {
      reminderConfig = { ...reminderForm };
    } else {
      reminderConfig = null;
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

  <!-- Produto / Serviço (optional) -->
  {#if productOptions.length > 0}
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div class="{formData.product ? 'sm:col-span-2' : 'sm:col-span-3'}">
        <label class="text-sm font-medium">Produto / Serviço</label>
        <div class="mt-1">
          <SearchableSelect
            bind:value={formData.product}
            options={productOptions}
            placeholder="Selecione (opcional)..."
            searchPlaceholder="Buscar produto..."
            emptyText="Nenhum produto encontrado."
          />
        </div>
      </div>
      {#if formData.product}
        <div>
          <label for="quantity" class="text-sm font-medium">Quantidade</label>
          <input
            id="quantity"
            type="number"
            step="0.01"
            min="0.01"
            bind:value={formData.quantity}
            class="border-input bg-background mt-1 flex h-9 w-full rounded-md border px-3 py-1 text-sm focus-visible:outline-none"
          />
        </div>
      {/if}
    </div>
  {/if}

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

    <!-- Parcela value preview -->
    {#if parcelaPreview}
      <div class="rounded-md border border-dashed px-3 py-2 text-xs">
        {#if parcelaPreview.mode === 'installment'}
          <p class="text-muted-foreground">
            <span class="font-medium text-foreground">{parcelaPreview.count}x</span> de
            <span class="font-medium text-foreground">{formData.currency} {parcelaPreview.valorEach.toFixed(2)}</span>
            <span class="ml-1">(valor total dividido em parcelas)</span>
          </p>
        {:else}
          <p class="text-muted-foreground">
            <span class="font-medium text-foreground">{formData.currency} {parcelaPreview.valorEach.toFixed(2)}</span>/cobr.
            <span class="ml-1">(valor cheio por parcela recorrente)</span>
          </p>
        {/if}
      </div>
    {/if}

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

  <!-- Inline Reminder Config (create mode only) -->
  {#if mode === 'create'}
    <div class="rounded-md border p-3 space-y-3">
      <label class="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          bind:checked={enableReminder}
          class="h-4 w-4 rounded border-gray-300"
        />
        <Bell class="size-4 text-muted-foreground" />
        <span class="font-medium">Configurar lembrete automático</span>
      </label>

      {#if enableReminder}
        <!-- Quick presets -->
        <div>
          <span class="mb-2 block text-xs font-medium text-muted-foreground">Presets Rápidos</span>
          <div class="flex flex-wrap gap-2">
            {#each QUICK_PRESETS as preset}
              <button
                type="button"
                class="inline-flex items-center rounded-md border px-2.5 py-1 text-xs transition-colors hover:bg-muted"
                onclick={() => applyQuickPreset(preset)}
              >
                <Zap class="mr-1 size-3" /> {preset.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- AI Copilot -->
        <AICopilot
          type="reminder"
          context={{ module_key: 'financeiro', tipo: formData.tipo || 'RECEBER' }}
          onGenerated={handleAIReminder}
        />

        <!-- Expandable detail config -->
        <button
          type="button"
          class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          onclick={() => (reminderExpanded = !reminderExpanded)}
        >
          {#if reminderExpanded}
            <ChevronDown class="size-3" />
          {:else}
            <ChevronRight class="size-3" />
          {/if}
          Configuração detalhada
        </button>

        {#if reminderExpanded}
          <div class="space-y-3 rounded-md border bg-muted/30 p-3">
            <div>
              <label for="rem-name" class="mb-1 block text-xs font-medium">Nome</label>
              <input
                id="rem-name"
                type="text"
                bind:value={reminderForm.name}
                placeholder="Ex: Lembrete de cobrança"
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
              />
            </div>

            <div>
              <label for="rem-trigger" class="mb-1 block text-xs font-medium">Tipo de Gatilho</label>
              <select
                id="rem-trigger"
                bind:value={reminderForm.trigger_type}
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
                onchange={() => {
                  if (reminderForm.trigger_type === 'due_date') {
                    reminderForm.trigger_config = { date_field: 'data_vencimento', offsets: [-3, 0, 3] };
                  } else {
                    reminderForm.trigger_config = { interval_days: 3, max_runs: 10, start_after: 'data_vencimento' };
                  }
                }}
              >
                {#each TRIGGER_OPTIONS as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>

            {#if reminderForm.trigger_type === 'due_date'}
              <div>
                <span class="mb-2 block text-xs font-medium">Dias relativos ao vencimento</span>
                <div class="flex flex-wrap gap-1.5">
                  {#each OFFSET_PRESETS as op}
                    <button
                      type="button"
                      class="rounded-full border px-2.5 py-1 text-xs transition-colors {(reminderForm.trigger_config.offsets || []).includes(op.value) ? 'border-primary bg-primary text-primary-foreground' : 'border-input bg-background hover:bg-muted'}"
                      onclick={() => toggleOffset(op.value)}
                    >
                      {op.label}
                    </button>
                  {/each}
                </div>
              </div>
            {:else}
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label for="rem-interval" class="mb-1 block text-xs font-medium">Intervalo (dias)</label>
                  <input
                    id="rem-interval"
                    type="number"
                    min="1"
                    max="90"
                    bind:value={reminderForm.trigger_config.interval_days}
                    class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
                  />
                </div>
                <div>
                  <label for="rem-max" class="mb-1 block text-xs font-medium">Máximo de execuções</label>
                  <input
                    id="rem-max"
                    type="number"
                    min="1"
                    max="100"
                    bind:value={reminderForm.trigger_config.max_runs}
                    class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
                  />
                </div>
              </div>
            {/if}

            <div>
              <label for="rem-channel" class="mb-1 block text-xs font-medium">Canal de Notificação</label>
              <select
                id="rem-channel"
                bind:value={reminderForm.channel_config.channel_type}
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
              >
                {#each CHANNEL_OPTIONS as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>

            <div class="flex items-center gap-2">
              <input
                id="rem-task"
                type="checkbox"
                bind:checked={reminderForm.task_config.enabled}
                class="size-4 rounded border-input"
              />
              <label for="rem-task" class="text-xs font-medium">Criar tarefa automaticamente</label>
            </div>

            <div>
              <label for="rem-msg" class="mb-1 block text-xs font-medium">
                Mensagem <span class="font-normal text-muted-foreground">(variáveis: &#123;&#123;contact_name&#125;&#125;, &#123;&#123;amount&#125;&#125;, &#123;&#123;due_date&#125;&#125;)</span>
              </label>
              <textarea
                id="rem-msg"
                bind:value={reminderForm.message_template}
                rows="2"
                placeholder="Lembrete: {{contact_name}} — {{amount}} {{currency}} vence em {{due_date}}"
                class="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
              ></textarea>
            </div>

            <div>
              <label for="rem-approval" class="mb-1 block text-xs font-medium">Aprovação</label>
              <select
                id="rem-approval"
                bind:value={reminderForm.approval_policy}
                class="border-input bg-background h-8 w-full rounded-md border px-3 text-sm"
              >
                <option value="auto">Automático</option>
                <option value="manual">Requer aprovação manual</option>
              </select>
            </div>
          </div>
        {/if}
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
