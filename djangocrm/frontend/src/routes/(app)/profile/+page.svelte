<script>
  import { enhance } from '$app/forms';
  import { invalidateAll } from '$app/navigation';
  import { toast } from 'svelte-sonner';
  import { User, Mail, Phone, Building2, Calendar, Edit, Save, X, Check, Camera } from '@lucide/svelte';
  import { validatePhoneNumber, formatPhoneNumber } from '$lib/utils/phone.js';
  import { formatDate, getInitials } from '$lib/utils/formatting.js';
  import PageHeader from '$lib/components/layout/PageHeader.svelte';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import * as Card from '$lib/components/ui/card/index.js';

  /** @type {{ data: import('./$types').PageData, form: import('./$types').ActionData }} */
  let { data, form } = $props();

  let isEditing = $state(false);
  let isSubmitting = $state(false);
  let phoneError = $state('');

  // Photo upload state
  let photoPreview = $state('');
  let photoFile = $state(null);
  /** @type {HTMLInputElement|null} */
  let photoInput = $state(null);

  // Form data state - initialized by $effect below
  let formData = $state({
    name: '',
    phone: ''
  });

  // Reset form data when not editing or when data changes
  $effect(() => {
    if (!isEditing) {
      formData = {
        name: data.user.name || '',
        phone: data.user.phone || ''
      };
      phoneError = '';
      photoPreview = data.user.profilePhoto || '';
      photoFile = null;
    }
  });

  // Handle form result
  $effect(() => {
    if (form?.success) {
      toast.success(form.message || 'Perfil atualizado com sucesso');
      invalidateAll();
    } else if (form?.error) {
      toast.error(form.error);
    }
  });

  const displayPhoto = $derived(photoPreview || data.user.profilePhoto || '');

  /**
   * @param {Event} e
   */
  function handlePhotoSelect(e) {
    const input = /** @type {HTMLInputElement} */ (e.target);
    const file = input.files?.[0];
    if (!file) return;

    const allowedTypes = ['image/png', 'image/jpeg', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato inválido. Use PNG, JPG ou WebP.');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Arquivo muito grande. Máximo 2MB.');
      return;
    }

    photoFile = file;
    const reader = new FileReader();
    reader.onload = () => {
      photoPreview = /** @type {string} */ (reader.result);
    };
    reader.readAsDataURL(file);
  }

  // Validate phone number on input
  function validatePhone() {
    if (!formData.phone.trim()) {
      phoneError = '';
      return;
    }

    const validation = validatePhoneNumber(formData.phone);
    if (!validation.isValid) {
      phoneError = validation.error || 'Invalid phone number';
    } else {
      phoneError = '';
    }
  }

  function toggleEdit() {
    isEditing = !isEditing;
    if (!isEditing) {
      // Reset form data when canceling edit
      formData = {
        name: data.user.name || '',
        phone: data.user.phone || ''
      };
      phoneError = '';
    }
  }

  // Handle form submission
  function handleSubmit() {
    isSubmitting = true;
    return async (
      /** @type {{ result: any, update: () => Promise<void> }} */ { result, update }
    ) => {
      isSubmitting = false;
      if (result.type === 'success') {
        isEditing = false;
      }
      await update();
    };
  }
</script>

<svelte:head>
  <title>Perfil - TalkHub CRM</title>
</svelte:head>

<PageHeader title="Perfil" subtitle="Gerencie suas informações pessoais">
  {#snippet actions()}
    <Button
      variant={isEditing ? 'outline' : 'default'}
      onclick={toggleEdit}
      disabled={isSubmitting}
    >
      {#if isEditing}
        <X class="mr-2 h-4 w-4" />
        Cancelar
      {:else}
        <Edit class="mr-2 h-4 w-4" />
        Editar Perfil
      {/if}
    </Button>
  {/snippet}
</PageHeader>

<div class="flex-1 space-y-6 p-4 md:p-6">
  <div class="mx-auto max-w-3xl space-y-6">
    <!-- Profile Header Card -->
    <Card.Root>
      <Card.Content class="p-6">
        <div class="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
          <!-- Avatar com upload -->
          <div class="relative">
            <div class="group relative h-20 w-20 overflow-hidden rounded-full">
              {#if displayPhoto}
                <img
                  src={displayPhoto}
                  alt={data.user.name || 'Perfil'}
                  class="h-full w-full object-cover"
                />
              {:else}
                <div class="flex h-full w-full items-center justify-center bg-[var(--color-primary-default)] text-xl text-white">
                  {getInitials(data.user.name)}
                </div>
              {/if}

              {#if isEditing}
                <button
                  type="button"
                  onclick={() => photoInput?.click()}
                  class="absolute inset-0 flex flex-col items-center justify-center gap-0.5 bg-black/50 opacity-0 transition-opacity group-hover:opacity-100"
                  aria-label="Alterar foto"
                >
                  <Camera class="h-5 w-5 text-white" />
                  <span class="text-[10px] text-white">Alterar</span>
                </button>
              {/if}
            </div>

            <input
              bind:this={photoInput}
              type="file"
              name="profile_photo"
              accept="image/png,image/jpeg,image/webp"
              class="hidden"
              form="profile-form"
              onchange={handlePhotoSelect}
            />

            {#if isEditing}
              <p class="text-muted-foreground mt-2 text-center text-[10px]">
                PNG, JPG ou WebP · Máx. 2MB
              </p>
            {/if}
          </div>

          <!-- User Info -->
          <div class="flex-1 text-center sm:text-left">
            <h2 class="text-foreground text-xl font-semibold">
              {data.user.name || 'Usuário sem nome'}
            </h2>
            <p class="text-muted-foreground">{data.user.email}</p>
            <div class="mt-3">
              <Badge variant={data.user.isActive ? 'default' : 'destructive'}>
                {data.user.isActive ? 'Ativo' : 'Inativo'}
              </Badge>
            </div>
          </div>
        </div>
      </Card.Content>
    </Card.Root>

    <!-- Profile Information Card -->
    <Card.Root>
      <Card.Header class="">
        <Card.Title class="">Informações do Perfil</Card.Title>
        <Card.Description class="">
          {isEditing
            ? 'Atualize seus dados pessoais abaixo'
            : 'Seus dados pessoais e informações da conta'}
        </Card.Description>
      </Card.Header>
      <Card.Content>
        {#if isEditing}
          <!-- Edit Form -->
          <form
            id="profile-form"
            method="POST"
            action="?/updateProfile"
            enctype="multipart/form-data"
            use:enhance={handleSubmit}
            class="space-y-6"
          >
            <div class="grid gap-6 sm:grid-cols-2">
              <!-- Name -->
              <div class="sm:col-span-2">
                <Label for="name" class="">Nome Completo *</Label>
                <Input
                  type="text"
                  id="name"
                  name="name"
                  bind:value={formData.name}
                  required
                  placeholder="Digite seu nome completo"
                  class="mt-1.5"
                />
              </div>

              <!-- Email (read-only) -->
              <div>
                <Label for="email" class="">Endereço de E-mail</Label>
                <Input
                  type="email"
                  id="email"
                  value={data.user.email}
                  disabled
                  class="bg-muted mt-1.5"
                />
                <p class="text-muted-foreground mt-1 text-xs">O e-mail não pode ser alterado</p>
              </div>

              <!-- Phone -->
              <div>
                <Label for="phone" class="">Telefone</Label>
                <Input
                  type="tel"
                  id="phone"
                  name="phone"
                  bind:value={formData.phone}
                  oninput={validatePhone}
                  placeholder="Digite seu telefone"
                  class="mt-1.5"
                />
                {#if phoneError}
                  <p class="text-destructive mt-1 text-sm">{phoneError}</p>
                {/if}
              </div>
            </div>

            <Separator />

            <div class="flex justify-end gap-3">
              <Button type="button" variant="outline" onclick={toggleEdit} disabled={isSubmitting}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting || !!phoneError}>
                {#if isSubmitting}
                  <svg class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    ></circle>
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Salvando...
                {:else}
                  <Save class="mr-2 h-4 w-4" />
                  Salvar Alterações
                {/if}
              </Button>
            </div>
          </form>
        {:else}
          <!-- View Mode -->
          <div class="grid gap-6 sm:grid-cols-2">
            <!-- Email -->
            <div class="space-y-1">
              <div class="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                <Mail class="h-4 w-4" />
                Endereço de E-mail
              </div>
              <p class="text-foreground">{data.user.email}</p>
            </div>

            <!-- Phone -->
            <div class="space-y-1">
              <div class="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                <Phone class="h-4 w-4" />
                Telefone
              </div>
              <p class="text-foreground">
                {data.user.phone ? formatPhoneNumber(data.user.phone) : 'Não informado'}
              </p>
            </div>

            <!-- Last Login -->
            <div class="space-y-1">
              <div class="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                <Calendar class="h-4 w-4" />
                Último Login
              </div>
              <p class="text-foreground">{formatDate(data.user.lastLogin)}</p>
            </div>

            <!-- Member Since -->
            <div class="space-y-1">
              <div class="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                <Calendar class="h-4 w-4" />
                Membro Desde
              </div>
              <p class="text-foreground">{formatDate(data.user.createdAt)}</p>
            </div>
          </div>
        {/if}
      </Card.Content>
    </Card.Root>

    <!-- Organizations Card -->
    {#if data.user.organizations && data.user.organizations.length > 0}
      <Card.Root>
        <Card.Header class="">
          <Card.Title class="">Organizações</Card.Title>
          <Card.Description class="">Organizações das quais você é membro</Card.Description>
        </Card.Header>
        <Card.Content class="space-y-4">
          {#each data.user.organizations as userOrg}
            <div class="bg-muted/30 flex items-center justify-between rounded-lg border p-4">
              <div class="flex items-center gap-3">
                <div
                  class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--color-primary-default)]"
                >
                  <Building2 class="h-5 w-5 text-white" />
                </div>
                <div>
                  <h4 class="text-foreground font-medium">
                    {userOrg.organization.name}
                  </h4>
                  <p class="text-muted-foreground text-sm">
                    Desde {formatDate(userOrg.joinedAt)}
                  </p>
                </div>
              </div>
              <Badge variant={userOrg.role === 'ADMIN' ? 'default' : 'secondary'}>
                {userOrg.role}
              </Badge>
            </div>
          {/each}
        </Card.Content>
      </Card.Root>
    {/if}
  </div>
</div>
