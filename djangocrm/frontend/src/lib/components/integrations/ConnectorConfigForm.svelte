<script>
  import { enhance } from '$app/forms';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Input } from '$lib/components/ui/input/index.js';
  import { Label } from '$lib/components/ui/label/index.js';
  import * as Select from '$lib/components/ui/select/index.js';
  import { Switch } from '$lib/components/ui/switch/index.js';
  import { Save } from '@lucide/svelte';

  /**
   * @typedef {Object} Props
   * @property {any[]} fields - JSON Schema-derived field definitions
   * @property {Record<string, any>} values - Current field values
   * @property {string} [action] - Form action URL
   * @property {boolean} [saving]
   */

  /** @type {Props} */
  let { fields = [], values = {}, action = '?/saveConfig', saving = false, showConnect = false } = $props();
</script>

<form method="POST" {action} use:enhance>
  <div class="space-y-4">
    {#each fields as field (field.name)}
      <div class="space-y-2">
        <Label for={field.name}>{field.label || field.name}</Label>
        {#if field.type === 'boolean'}
          <div class="flex items-center gap-2">
            <Switch id={field.name} name={field.name} checked={values[field.name] || false} />
            {#if field.description}
              <span class="text-muted-foreground text-xs">{field.description}</span>
            {/if}
          </div>
        {:else if field.type === 'select' && field.options}
          <Select.Root type="single" name={field.name} value={values[field.name] || ''}>
            <Select.Trigger class="w-full">
              {values[field.name] || field.placeholder || 'Selecione...'}
            </Select.Trigger>
            <Select.Content>
              {#each field.options as opt}
                <Select.Item value={opt.value}>{opt.label}</Select.Item>
              {/each}
            </Select.Content>
          </Select.Root>
        {:else}
          <Input
            id={field.name}
            name={field.name}
            type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
            placeholder={field.placeholder || ''}
            value={values[field.name] || ''}
            required={field.required || false}
          />
        {/if}
        {#if field.description && field.type !== 'boolean'}
          <p class="text-muted-foreground text-xs">{field.description}</p>
        {/if}
      </div>
    {/each}

    <div class="flex gap-2">
      <Button type="submit" disabled={saving} class="gap-2">
        <Save class="size-4" />
        {saving ? 'Salvando...' : 'Salvar Configuração'}
      </Button>
      {#if showConnect}
        <Button type="submit" formaction="?/saveAndConnect" variant="default" disabled={saving} class="gap-2">
          <Save class="size-4" />
          Salvar e Conectar
        </Button>
      {/if}
    </div>
  </div>
</form>
