<script>
  import { X } from '@lucide/svelte';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import EditableMultiSelect from '$lib/components/ui/editable-field/EditableMultiSelect.svelte';

  /**
   * @typedef {Object} User
   * @property {string} id
   * @property {string} name
   * @property {string} email
   */

  /**
   * @typedef {Object} Team
   * @property {string} [id]
   * @property {string} name
   * @property {string} [description]
   * @property {string[]} [userIds]
   */

  /**
   * @type {{
   *   open?: boolean,
   *   team?: Team | null,
   *   users?: User[],
   *   onClose?: () => void,
   *   onSubmit?: (data: { name: string, description: string, users: string[], teamId?: string }) => void,
   *   isLoading?: boolean
   * }}
   */
  let {
    open = $bindable(false),
    team = null,
    users = [],
    onClose,
    onSubmit,
    isLoading = false
  } = $props();

  // Form state
  let formName = $state('');
  let formDescription = $state('');
  let formUsers = $state(/** @type {string[]} */ ([]));

  // Reset form when dialog opens/closes or team changes
  $effect(() => {
    if (open) {
      formName = team?.name || '';
      formDescription = team?.description || '';
      formUsers = team?.userIds || [];
    }
  });

  const isEditing = $derived(!!team?.id);
  const dialogTitle = $derived(isEditing ? 'Editar Equipe' : 'Criar Equipe');
  const submitLabel = $derived(isEditing ? 'Salvar Alterações' : 'Criar Equipe');

  // Transform users for multi-select
  const userOptions = $derived(
    users.map((u) => ({
      id: u.id,
      name: u.name,
      email: u.email
    }))
  );

  function handleClose() {
    open = false;
    onClose?.();
  }

  /**
   * @param {Event} e
   */
  function handleSubmit(e) {
    e.preventDefault();
    if (!formName.trim()) return;

    onSubmit?.({
      name: formName.trim(),
      description: formDescription.trim(),
      users: formUsers,
      teamId: team?.id
    });
  }

  /**
   * @param {string[]} value
   */
  function handleUsersChange(value) {
    formUsers = value;
  }
</script>

<Dialog.Root bind:open onOpenChange={(o) => !o && handleClose()}>
  <Dialog.Content class="sm:max-w-[500px]" portalProps={{}}>
    <Dialog.Header class="">
      <Dialog.Title class="">{dialogTitle}</Dialog.Title>
      <Dialog.Description class="">
        {isEditing
          ? 'Atualize os detalhes da equipe e as atribuições de membros.'
          : 'Crie uma nova equipe para agrupar usuários para atribuições.'}
      </Dialog.Description>
    </Dialog.Header>

    <form onsubmit={handleSubmit} class="space-y-4">
      <div class="space-y-2">
        <Label class="" for="team-name">Nome da Equipe *</Label>
        <Input
          id="team-name"
          bind:value={formName}
          placeholder="ex.: Equipe de Vendas"
          required
          disabled={isLoading}
        />
      </div>

      <div class="space-y-2">
        <Label class="" for="team-description">Descrição</Label>
        <textarea
          id="team-description"
          bind:value={formDescription}
          placeholder="Descreva o propósito da equipe..."
          rows="3"
          disabled={isLoading}
          class="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex min-h-[80px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        ></textarea>
      </div>

      <div class="space-y-2">
        <Label class="">Atribuir Membros</Label>
        <EditableMultiSelect
          value={formUsers}
          options={userOptions}
          placeholder="Selecione os membros da equipe..."
          emptyText="Nenhum membro atribuído"
          onchange={handleUsersChange}
          disabled={isLoading}
          class="rounded-md border p-1"
        />
        <p class="text-muted-foreground text-xs">
          Os membros da equipe poderão acessar registros atribuídos a esta equipe.
        </p>
      </div>

      <Dialog.Footer class="gap-2 sm:gap-0">
        <Button type="button" variant="outline" onclick={handleClose} disabled={isLoading}>
          Cancelar
        </Button>
        <Button type="submit" disabled={isLoading || !formName.trim()}>
          {isLoading ? 'Salvando...' : submitLabel}
        </Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
