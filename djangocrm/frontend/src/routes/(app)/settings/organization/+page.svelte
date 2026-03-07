<script>
  import { enhance } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import {
    Building2,
    Globe,
    Banknote,
    Sparkles,
    Check,
    MapPin,
    Hash,
    FileText,
    Loader2,
    Camera,
    X
  } from '@lucide/svelte';
  import { PageHeader } from '$lib/components/layout';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  const settings = $derived(data.settings || {});
  let isLoading = $state(false);

  // Opções de moeda
  const currencyOptions = CURRENCY_CODES.filter((c) => c.value);

  // Opções de país
  const countryOptions = [
    { value: '', label: 'Selecionar País', flag: '' },
    { value: 'BR', label: 'Brasil', flag: '🇧🇷' },
    { value: 'US', label: 'Estados Unidos', flag: '🇺🇸' },
    { value: 'GB', label: 'Reino Unido', flag: '🇬🇧' },
    { value: 'CA', label: 'Canadá', flag: '🇨🇦' },
    { value: 'AU', label: 'Austrália', flag: '🇦🇺' },
    { value: 'DE', label: 'Alemanha', flag: '🇩🇪' },
    { value: 'FR', label: 'França', flag: '🇫🇷' },
    { value: 'IN', label: 'Índia', flag: '🇮🇳' },
    { value: 'JP', label: 'Japão', flag: '🇯🇵' },
    { value: 'SG', label: 'Singapura', flag: '🇸🇬' },
    { value: 'AE', label: 'Emirados Árabes', flag: '🇦🇪' },
    { value: 'MX', label: 'México', flag: '🇲🇽' },
    { value: 'CH', label: 'Suíça', flag: '🇨🇭' },
    { value: 'NL', label: 'Holanda', flag: '🇳🇱' },
    { value: 'ES', label: 'Espanha', flag: '🇪🇸' },
    { value: 'IT', label: 'Itália', flag: '🇮🇹' },
    { value: 'PT', label: 'Portugal', flag: '🇵🇹' },
    { value: 'AR', label: 'Argentina', flag: '🇦🇷' },
    { value: 'CL', label: 'Chile', flag: '🇨🇱' },
    { value: 'CO', label: 'Colômbia', flag: '🇨🇴' }
  ];

  // Estado do formulário
  let formName = $state('');
  let formDomain = $state('');
  let formDescription = $state('');
  let formCurrency = $state('BRL');
  let formCountry = $state('');

  // Estado do upload de logo
  let logoPreview = $state('');
  let logoFile = $state(null);
  let isUploadingLogo = $state(false);

  /** @type {HTMLInputElement|null} */
  let logoInput = $state(null);

  // Atualizar estado quando settings mudar
  $effect(() => {
    formName = settings.name || '';
    formDomain = settings.domain || '';
    formDescription = settings.description || '';
    formCurrency = settings.default_currency || 'BRL';
    formCountry = settings.default_country || '';
    logoPreview = settings.logo_url || '';
  });

  // Resultado do formulário
  $effect(() => {
    if (form?.success) {
      toast.success('Configurações da organização atualizadas');
      invalidateAll();
    } else if (form?.error) {
      toast.error(form.error);
    }
  });

  // Bandeira do país selecionado
  const currentCountryFlag = $derived(
    countryOptions.find((c) => c.value === formCountry)?.flag || ''
  );

  // Símbolo da moeda
  const currencySymbol = $derived(() => {
    try {
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: formCurrency
      })
        .format(0)
        .replace(/[\d.,\s]/g, '');
    } catch {
      return '$';
    }
  });

  // Iniciais da organização
  const orgInitials = $derived(
    formName
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || 'OR'
  );

  // Tem logo salvo ou preview
  const hasLogo = $derived(logoPreview && logoPreview.length > 0);

  /**
   * @param {Event} e
   */
  function handleLogoSelect(e) {
    const input = /** @type {HTMLInputElement} */ (e.target);
    const file = input.files?.[0];
    if (!file) return;

    // Validar tipo
    const allowedTypes = ['image/png', 'image/jpeg', 'image/svg+xml'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato inválido. Use PNG, JPG ou SVG.');
      return;
    }

    // Validar tamanho (2MB)
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Arquivo muito grande. Máximo 2MB.');
      return;
    }

    logoFile = file;
    const reader = new FileReader();
    reader.onload = () => {
      logoPreview = /** @type {string} */ (reader.result);
    };
    reader.readAsDataURL(file);
  }

  function removeLogo() {
    logoFile = null;
    logoPreview = '';
    if (logoInput) logoInput.value = '';
  }
</script>

<svelte:head>
  <title>Configurações da Organização - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Configurações da Organização" subtitle="Gerencie as preferências da sua organização">
  {#snippet actions()}
    <Button type="submit" form="org-settings-form" disabled={isLoading} class="gap-2">
      {#if isLoading}
        <Loader2 class="h-4 w-4 animate-spin" />
        Salvando...
      {:else}
        <Check class="h-4 w-4" />
        Salvar Alterações
      {/if}
    </Button>
  {/snippet}
</PageHeader>

<div class="flex-1 p-4 md:p-6 lg:p-8">
  <form
    id="org-settings-form"
    method="POST"
    action="?/update"
    enctype="multipart/form-data"
    use:enhance={() => {
      isLoading = true;
      return async ({ update }) => {
        await update();
        isLoading = false;
      };
    }}
    class="mx-auto max-w-4xl space-y-8"
  >
    <!-- Seção: Identidade da Organização -->
    <section class="section-reveal">
      <div class="gradient-border overflow-hidden">
        <div class="relative p-8 md:p-10">
          <div class="pointer-events-none absolute inset-0 overflow-hidden">
            <div
              class="absolute -top-20 -right-20 h-64 w-64 rounded-full bg-gradient-to-br from-[var(--accent-primary)] to-transparent opacity-10 blur-3xl"
            ></div>
            <div
              class="absolute -bottom-32 -left-32 h-80 w-80 rounded-full bg-gradient-to-tr from-[var(--accent-secondary)] to-transparent opacity-10 blur-3xl"
            ></div>
          </div>

          <div class="relative flex flex-col gap-8 md:flex-row md:items-start">
            <!-- Avatar / Logo da Organização -->
            <div class="flex flex-col items-center gap-4">
              <div class="relative">
                <div
                  class="pulse-ring absolute -inset-2 rounded-3xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] opacity-30"
                ></div>

                <div
                  class="org-avatar group relative flex h-28 w-28 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] shadow-2xl"
                >
                  {#if hasLogo}
                    <img src={logoPreview} alt="Logo da organização" class="h-full w-full object-cover" />
                  {:else}
                    <span class="text-3xl font-bold text-white">{orgInitials}</span>
                  {/if}

                  <!-- Overlay de upload -->
                  <button
                    type="button"
                    onclick={() => logoInput?.click()}
                    class="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/50 opacity-0 transition-opacity group-hover:opacity-100"
                    aria-label="Alterar logo"
                  >
                    <Camera class="h-5 w-5 text-white" />
                    <span class="text-xs text-white">Alterar</span>
                  </button>
                </div>

                {#if hasLogo}
                  <button
                    type="button"
                    onclick={removeLogo}
                    class="absolute -top-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-white shadow-md transition-transform hover:scale-110"
                    aria-label="Remover logo"
                  >
                    <X class="h-3.5 w-3.5" />
                  </button>
                {/if}
              </div>

              <input
                bind:this={logoInput}
                type="file"
                name="logo"
                accept="image/png,image/jpeg,image/svg+xml"
                class="hidden"
                onchange={handleLogoSelect}
              />
              <p class="text-muted-foreground text-center text-xs">
                PNG, JPG ou SVG<br />Máx. 2MB
              </p>
            </div>

            <!-- Dados da Organização -->
            <div class="flex-1 space-y-6">
              <div class="space-y-1">
                <div
                  class="text-muted-foreground mb-2 flex items-center gap-2 text-xs font-medium tracking-wider uppercase"
                >
                  <Building2 class="h-3.5 w-3.5" />
                  Identidade da Organização
                </div>
              </div>

              <div class="grid gap-5 md:grid-cols-2">
                <!-- Nome da Organização -->
                <div class="space-y-2">
                  <Label for="name" class="text-muted-foreground flex items-center gap-2 text-sm">
                    <Hash class="h-3.5 w-3.5" />
                    Nome da Organização
                  </Label>
                  <div class="input-glow rounded-lg transition-shadow duration-300">
                    <Input
                      id="name"
                      name="name"
                      type="text"
                      bind:value={formName}
                      placeholder="Minha Empresa Ltda"
                      class="h-11 border-[var(--border-default)] bg-[var(--bg-subtle)] text-base transition-colors focus:border-[var(--accent-primary)] focus:bg-transparent"
                    />
                  </div>
                </div>

                <!-- Domínio -->
                <div class="space-y-2">
                  <Label for="domain" class="text-muted-foreground flex items-center gap-2 text-sm">
                    <Globe class="h-3.5 w-3.5" />
                    Domínio da Empresa
                  </Label>
                  <div class="input-glow rounded-lg transition-shadow duration-300">
                    <div class="relative flex items-center">
                      <div class="pointer-events-none absolute left-3 flex items-center">
                        <Globe class="text-muted-foreground h-4 w-4" />
                      </div>
                      <Input
                        id="domain"
                        name="domain"
                        type="text"
                        bind:value={formDomain}
                        placeholder="suaempresa.com.br"
                        class="h-11 border-[var(--border-default)] bg-[var(--bg-subtle)] pl-10 text-base transition-colors focus:border-[var(--accent-primary)] focus:bg-transparent"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- Descrição -->
              <div class="space-y-2">
                <Label
                  for="description"
                  class="text-muted-foreground flex items-center gap-2 text-sm"
                >
                  <FileText class="h-3.5 w-3.5" />
                  Sobre a Organização
                </Label>
                <div class="input-glow rounded-lg transition-shadow duration-300">
                  <textarea
                    id="description"
                    name="description"
                    rows="3"
                    bind:value={formDescription}
                    placeholder="Breve descrição da sua organização, setor de atuação e o que vocês fazem..."
                    class="border-input ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex min-h-[100px] w-full resize-none rounded-lg border bg-[var(--bg-subtle)] px-4 py-3 text-base transition-colors focus:border-[var(--accent-primary)] focus:bg-transparent focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  ></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Seção: Moeda e Localidade -->
    <section class="section-reveal delay-1">
      <div class="gradient-border overflow-hidden">
        <div class="relative p-8 md:p-10">
          <div class="pointer-events-none absolute inset-0 overflow-hidden">
            <div
              class="absolute top-10 -left-20 h-48 w-48 rounded-full bg-gradient-to-br from-[var(--status-success)] to-transparent opacity-10 blur-3xl"
            ></div>
          </div>

          <div class="relative space-y-8">
            <div class="flex items-center justify-between">
              <div class="space-y-1">
                <div
                  class="text-muted-foreground mb-2 flex items-center gap-2 text-xs font-medium tracking-wider uppercase"
                >
                  <Globe class="h-3.5 w-3.5" />
                  Configurações Regionais
                </div>
                <h3 class="text-lg font-semibold">Moeda e Localidade</h3>
                <p class="text-muted-foreground text-sm">
                  Configure a moeda padrão e preferências regionais
                </p>
              </div>
            </div>

            <div class="grid gap-6 lg:grid-cols-2">
              <!-- Seleção de Moeda -->
              <div class="space-y-3">
                <Label
                  for="default_currency"
                  class="text-muted-foreground flex items-center gap-2 text-sm"
                >
                  <Banknote class="h-3.5 w-3.5" />
                  Moeda Padrão
                </Label>
                <div class="input-glow rounded-lg transition-shadow duration-300">
                  <div class="relative">
                    <select
                      id="default_currency"
                      name="default_currency"
                      bind:value={formCurrency}
                      class="custom-select border-input h-12 w-full cursor-pointer rounded-lg border bg-[var(--bg-subtle)] px-4 text-base transition-colors focus:border-[var(--accent-primary)] focus:bg-transparent focus:ring-2 focus:ring-[var(--accent-primary-subtle)] focus:outline-none"
                    >
                      {#each currencyOptions as currency}
                        <option value={currency.value}>{currency.label}</option>
                      {/each}
                    </select>
                  </div>
                </div>
                <p class="text-muted-foreground text-xs">
                  Aplicada em oportunidades, faturas e relatórios financeiros
                </p>
              </div>

              <!-- Seleção de País -->
              <div class="space-y-3">
                <Label
                  for="default_country"
                  class="text-muted-foreground flex items-center gap-2 text-sm"
                >
                  <MapPin class="h-3.5 w-3.5" />
                  País Padrão
                </Label>
                <div class="input-glow rounded-lg transition-shadow duration-300">
                  <div class="relative">
                    <select
                      id="default_country"
                      name="default_country"
                      bind:value={formCountry}
                      class="custom-select border-input h-12 w-full cursor-pointer rounded-lg border bg-[var(--bg-subtle)] px-4 text-base transition-colors focus:border-[var(--accent-primary)] focus:bg-transparent focus:ring-2 focus:ring-[var(--accent-primary-subtle)] focus:outline-none"
                    >
                      {#each countryOptions as country}
                        <option value={country.value}>{country.flag} {country.label}</option>
                      {/each}
                    </select>
                  </div>
                </div>
                <p class="text-muted-foreground text-xs">
                  Usado para endereços, formatos de data e configurações de localidade
                </p>
              </div>
            </div>

            <!-- Preview da Moeda -->
            {#if formCurrency}
              <div
                class="relative overflow-hidden rounded-xl bg-gradient-to-br from-[var(--bg-subtle)] to-[var(--bg-muted)] p-6"
              >
                <div class="shimmer absolute inset-0"></div>
                <div class="relative">
                  <div class="mb-3 flex items-center gap-2">
                    <Sparkles class="h-4 w-4 text-[var(--accent-secondary)]" />
                    <span class="text-muted-foreground text-sm font-medium">Prévia da Moeda</span>
                  </div>
                  <div class="flex items-baseline gap-3">
                    <span class="text-gradient text-4xl font-bold tracking-tight md:text-5xl">
                      {new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: formCurrency,
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0
                      }).format(125000)}
                    </span>
                    <span class="text-muted-foreground text-lg">
                      {currentCountryFlag}
                    </span>
                  </div>
                  <div class="text-muted-foreground mt-2 text-sm">
                    Exemplo: {new Intl.NumberFormat('pt-BR', {
                      style: 'currency',
                      currency: formCurrency
                    }).format(12345.67)}
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </section>

    <!-- Rodapé com status -->
    <section class="section-reveal delay-2">
      <div
        class="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4"
      >
        <div class="flex items-center gap-6">
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full bg-[var(--status-success)]"></div>
            <span class="text-muted-foreground text-sm">Configurações sincronizadas</span>
          </div>
          <div class="text-muted-foreground text-sm">
            Última atualização: {new Date().toLocaleDateString('pt-BR', {
              day: '2-digit',
              month: 'short',
              year: 'numeric'
            })}
          </div>
        </div>
        <Button
          type="submit"
          disabled={isLoading}
          size="lg"
          class="gap-2 bg-gradient-to-r from-[var(--accent-primary)] to-[var(--stage-qualified)] text-white shadow-[var(--accent-primary)]/25 shadow-lg transition-all hover:shadow-[var(--accent-primary)]/30 hover:shadow-xl"
        >
          {#if isLoading}
            <Loader2 class="h-4 w-4 animate-spin" />
            Salvando...
          {:else}
            <Check class="h-4 w-4" />
            Salvar Todas as Alterações
          {/if}
        </Button>
      </div>
    </section>
  </form>
</div>

<style>
  @keyframes float {
    0%,
    100% {
      transform: translateY(0) rotate(0deg);
    }
    50% {
      transform: translateY(-8px) rotate(2deg);
    }
  }

  @keyframes pulse-ring {
    0% {
      transform: scale(0.95);
      opacity: 0.5;
    }
    50% {
      transform: scale(1.05);
      opacity: 0.3;
    }
    100% {
      transform: scale(0.95);
      opacity: 0.5;
    }
  }

  @keyframes shimmer-slide {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }

  .org-avatar {
    animation: float 6s ease-in-out infinite;
  }

  .pulse-ring {
    animation: pulse-ring 3s ease-in-out infinite;
  }

  .shimmer::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
    animation: shimmer-slide 3s ease-in-out infinite;
  }

  .custom-select {
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 40px;
  }

  .gradient-border {
    position: relative;
    background: var(--card);
    border-radius: var(--radius-xl);
  }

  .gradient-border::before {
    content: '';
    position: absolute;
    inset: 0;
    padding: 1px;
    border-radius: inherit;
    background: linear-gradient(
      135deg,
      var(--accent-primary),
      transparent 50%,
      var(--accent-secondary)
    );
    -webkit-mask:
      linear-gradient(#fff 0 0) content-box,
      linear-gradient(#fff 0 0);
    mask:
      linear-gradient(#fff 0 0) content-box,
      linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0.5;
    transition: opacity 0.3s ease;
  }

  .gradient-border:hover::before {
    opacity: 1;
  }

  .input-glow:focus-within {
    box-shadow:
      0 0 0 2px var(--accent-primary-subtle),
      0 0 20px -5px var(--accent-primary);
  }

  .section-reveal {
    opacity: 0;
    transform: translateY(20px);
    animation: reveal 0.6s ease forwards;
  }

  @keyframes reveal {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .delay-1 {
    animation-delay: 0.1s;
  }
  .delay-2 {
    animation-delay: 0.2s;
  }
</style>
